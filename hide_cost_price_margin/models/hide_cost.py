# -*- coding: utf-8 -*-
"""Hide cost price and margin from users who are not in the "Show Cost Price & Margin" group.

Two layers:

* Default mode (always on): the fields are removed from every view of the affected models (and from
  x2many sub-views embedded in other views), left out of ``fields_get`` (export and import dialogs,
  pivot measures) and blocked in ``export_data``. Python code of other modules keeps reading the
  values normally, so prices, margins and stock valuation keep computing.
* Strict mode (setting): product cost and sale margin fields also get hard field-level access checks, so reading, writing or
  grouping them over RPC raises an access error, exactly as if they had ``groups=`` on the field.
"""
import re

from lxml import etree

from odoo import _, api, models
from odoo.exceptions import AccessError

GROUP_XMLID = 'hide_cost_price_margin.group_show_cost_price'
STRICT_PARAM = 'hide_cost_price_margin.strict_mode'

# model -> field names hidden from users without the group (only fields that exist are used)
HIDDEN_FIELDS = {
    'product.template': frozenset({'standard_price'}),
    'product.product': frozenset({'standard_price', 'avg_cost', 'total_value', 'value_svl'}),
    'sale.order': frozenset({'margin', 'margin_percent'}),
    'sale.order.line': frozenset({'purchase_price', 'margin', 'margin_percent'}),
    'stock.lot': frozenset({'standard_price', 'avg_cost', 'total_value', 'value_svl'}),
    'stock.move': frozenset({'standard_price', 'value', 'value_manual', 'remaining_value'}),
}

# subset that strict mode also blocks at field level. Stock valuation fields stay out: the stock engine
# writes them as the warehouse user, so a hard block there would stop receipts and deliveries.
STRICT_FIELDS = {
    'product.template': frozenset({'standard_price'}),
    'product.product': frozenset({'standard_price'}),
    'sale.order': frozenset({'margin', 'margin_percent'}),
    'sale.order.line': frozenset({'purchase_price', 'margin', 'margin_percent'}),
}

# elements (by their name attribute) that only wrap a hidden field and are hidden with it
WRAPPER_NAMES = {
    'product.template': frozenset({'standard_price_uom'}),
    'product.product': frozenset({'standard_price_uom'}),
}

_TRUE = ('1', 'True', 'true')


def hidden_names(env, model_name):
    """Hidden field names of ``model_name`` that exist in this database."""
    names = HIDDEN_FIELDS.get(model_name)
    if not names or model_name not in env:
        return frozenset()
    fields = env[model_name]._fields
    return frozenset(name for name in names if name in fields)


def mark_arch(env, root, model_name):
    """Put the cost group on every node of ``root`` that shows a hidden field.

    ``root`` is the combined view architecture (lxml element) of ``model_name``. Sub-views of x2many
    fields are walked with their own model. Returns the number of marked nodes.
    """
    to_hide = []

    def walk(node, model):
        hidden = hidden_names(env, model)
        wrappers = WRAPPER_NAMES.get(model, frozenset())
        model_fields = env[model]._fields if model in env else {}
        for child in node:
            if not isinstance(child.tag, str):
                continue  # comments, processing instructions
            if child.tag == 'field':
                name = child.get('name')
                if name in hidden:
                    to_hide.append(child)
                    continue
                field = model_fields.get(name)
                if field is not None and field.type in ('one2many', 'many2many') and len(child):
                    walk(child, field.comodel_name)
            elif child.tag == 'label' and child.get('for') in hidden:
                to_hide.append(child)
            elif child.get('name') in wrappers:
                to_hide.append(child)
            else:
                walk(child, model)

    walk(root, model_name)
    if not to_hide:
        return 0

    hidden_set = set(to_hide)

    def only_hidden(container):
        """True when every field and label inside ``container`` is hidden or a pure invisible helper."""
        for sub in container.iter('field', 'label'):
            if sub in hidden_set or any(anc in hidden_set for anc in sub.iterancestors()):
                continue
            if sub.tag == 'field' and sub.get('invisible') in _TRUE:
                continue
            return False
        return True

    targets = []
    for node in to_hide:
        target = node
        parent = node.getparent()
        while parent is not None and parent.tag in ('div', 'span') and only_hidden(parent):
            target = parent
            parent = parent.getparent()
        if target not in targets:
            targets.append(target)

    for target in targets:
        groups = (target.get('groups') or '').strip()
        if not groups or groups == 'base.group_user':
            target.set('groups', GROUP_XMLID)
        else:
            # keep the existing restriction and add ours: <t groups="ours"><node groups="theirs"/></t>
            wrapper = etree.Element('t', groups=GROUP_XMLID)
            target.addprevious(wrapper)
            wrapper.tail = target.tail
            target.tail = None
            wrapper.append(target)
    return len(targets)


class Base(models.AbstractModel):
    _inherit = 'base'

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @api.model
    def _hcp_is_strict(self):
        Param = self.env['ir.config_parameter'].sudo()
        if hasattr(Param, 'get_bool'):  # 20.0+
            return Param.get_bool(STRICT_PARAM)
        return str(Param.get_param(STRICT_PARAM, 'False')) in _TRUE

    @api.model
    def _hcp_hidden_for_user(self):
        """Hidden field names of this model for the current user (empty when the user may see costs)."""
        names = hidden_names(self.env, self._name)
        if not names or self.env.su or self.env.user.has_group(GROUP_XMLID):
            return frozenset()
        return names

    # ------------------------------------------------------------------
    # views
    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        # The combined arch is cached for all users; group-restricted nodes are removed per user later.
        mark_arch(self.env, arch, self._name)
        return arch, view

    @api.model
    def get_views(self, views, options=None):
        result = super(Base, self.with_context(hcp_from_get_views=True)).get_views(views, options)
        archs = ' '.join(view.get('arch') or '' for view in result.get('views', {}).values())
        for model_name, info in result.get('models', {}).items():
            if model_name not in self.env:
                continue
            hidden = self.env[model_name]._hcp_hidden_for_user()
            if not hidden:
                continue
            fields = info.get('fields') if isinstance(info.get('fields'), dict) else info
            for name in hidden:
                # drop the definition only when no remaining node of the views uses it
                if name in fields and not re.search(r'\b%s\b' % re.escape(name), archs):
                    del fields[name]
        return result

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if not self.env.context.get('hcp_from_get_views'):
            for name in self._hcp_hidden_for_user():
                res.pop(name, None)
        return res

    # ------------------------------------------------------------------
    # export guard (default mode)
    # ------------------------------------------------------------------
    def _hcp_check_export_paths(self, fields_to_export):
        for path in fields_to_export:
            model = self
            for part in re.split(r'[/.:]', path or ''):
                if not part or part == 'id':
                    break
                field = model._fields.get(part)
                if field is None:
                    break
                if part in model._hcp_hidden_for_user():
                    raise AccessError(_(
                        'You are not allowed to export "%(field)s" (%(model)s). '
                        'Ask an administrator for the "Show Cost Price & Margin" access.',
                        field=field.string, model=model._name,
                    ))
                if not field.relational:
                    break
                model = self.env[field.comodel_name]

    def export_data(self, fields_to_export):
        self._hcp_check_export_paths(fields_to_export)
        return super().export_data(fields_to_export)

    # ------------------------------------------------------------------
    # strict mode: hard field-level access
    # ------------------------------------------------------------------
    def _hcp_strict_blocked(self, field_name):
        if self.env.su or field_name not in STRICT_FIELDS.get(self._name, ()):
            return False
        return self._hcp_is_strict() and not self.env.user.has_group(GROUP_XMLID)

    if hasattr(models.BaseModel, '_has_field_access'):
        @api.model
        def _has_field_access(self, field, operation):
            if self._hcp_strict_blocked(field.name):
                return False
            return super()._has_field_access(field, operation)
    else:
        @api.model
        def check_field_access_rights(self, operation, field_names):
            res = super().check_field_access_rights(operation, field_names)
            if self.env.su or self._name not in STRICT_FIELDS:
                return res
            if not field_names:
                return [name for name in res if not self._hcp_strict_blocked(name)]
            blocked = sorted({name for name in field_names if self._hcp_strict_blocked(name)})
            if blocked:
                raise AccessError(_(
                    'You do not have enough rights to access the fields "%(fields)s" on %(model)s. '
                    'Ask an administrator for the "Show Cost Price & Margin" access.\n\n(Operation: %(operation)s)',
                    fields=','.join(blocked), model=self._name, operation=operation,
                ))
            return res
