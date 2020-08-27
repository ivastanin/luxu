# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz

from odoo import api, fields, models, tools, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dt
_logger = logging.getLogger(__name__)


"""
class AssetFolio(models.Model):

    _inherit = 'asset.folio'
    _order = 'reservation_id desc'

    reservation_id = fields.Many2one('asset.reservation', string='Reservation')

    @api.multi
    def write(self, vals):
        context = dict(self._context)
        if not context:
            context = {}
        context.update({'from_reservation': True})
        res = super(AssetFolio, self).write(vals)
        reservation_line_obj = self.env['account.asset.asset.reservation.line']
        for folio_obj in self:
            if folio_obj.reservation_id:
                for reservation in folio_obj.reservation_id:
                    reservation_obj = (reservation_line_obj.search
                                       ([('reservation_id', '=',
                                          reservation.id)]))
                    if len(reservation_obj) == 1:
                        for line_id in reservation.reservation_line:
                            line_id = line_id.reserve
                            for asset_id in line_id:
                                vals = {'asset_id': asset_id.id,
                                        'check_in': folio_obj.checkin_date,
                                        'check_out': folio_obj.checkout_date,
                                        'state': 'assigned',
                                        'reservation_id': reservation.id,
                                        }
                                reservation_obj.write(vals)
        return res


class AssetFolioLineExt(models.Model):

    _inherit = 'asset.folio.line'

    @api.onchange('checkin_date', 'checkout_date')
    def on_change_checkout(self):
        res = super(AssetFolioLineExt, self).on_change_checkout()
        account_asset_obj = self.env['account.asset.asset']
        avail_prod_ids = []
        asset_asset_ids = account_asset_obj.search([])
        for asset in asset_asset_ids:
            assigned = False
            for line in asset.asset_reservation_line_ids:
                if line.status != 'cancel':
                    if(self.checkin_date <= line.check_in <=
                        self.checkout_date) or (self.checkin_date <=
                                                line.check_out <=
                                                self.checkout_date):
                        assigned = True
                    elif(line.check_in <= self.checkin_date <=
                         line.check_out) or (line.check_in <=
                                             self.checkout_date <=
                                             line.check_out):
                        assigned = True
            if not assigned:
                avail_prod_ids.append(asset.product_id.id)
        return res

    @api.multi
    def write(self, vals):

        reservation_line_obj = self.env['account.asset.asset.reservation.line']
        asset_obj = self.env['account.asset.asset']
        prod_id = vals.get('product_id') or self.product_id.id
        chkin = vals.get('checkin_date') or self.checkin_date
        chkout = vals.get('checkout_date') or self.checkout_date
        is_reserved = self.is_reserved
        if prod_id and is_reserved:
            prod_domain = [('product_id', '=', prod_id)]
            prod_room = asset_obj.search(prod_domain, limit=1)
            if (self.product_id and self.checkin_date and self.checkout_date):
                old_prd_domain = [('product_id', '=', self.product_id.id)]
                old_prod_room = asset_obj.search(old_prd_domain, limit=1)
                if prod_room and old_prod_room:
                    # Check for existing asset lines.
                    srch_rmline = [('asset_id', '=', old_prod_room.id),
                                   ('check_in', '=', self.checkin_date),
                                   ('check_out', '=', self.checkout_date),
                                   ]
                    rm_lines = reservation_line_obj.search(srch_rmline)
                    if rm_lines:
                        rm_line_vals = {'asset_id': prod_room.id,
                                        'check_in': chkin,
                                        'check_out': chkout}
                        rm_lines.write(rm_line_vals)
        return super(AssetFolioLineExt, self).write(vals)
"""

class AssetReservation(models.Model):

    _name = "asset.reservation"
    _rec_name = "reservation_no"
    _description = "Reservation"
    _order = 'reservation_no desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    reservation_no = fields.Char('Reservation No', size=64, readonly=True)
    date_order = fields.Datetime('Date Ordered', readonly=True, required=True,
                                 index=True,
                                 default=(lambda *a: time.strftime(dt)))
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True,
                                 index=True,
                                 required=True,
                                 states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one('product.pricelist', 'Scheme',
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   help="Pricelist for current reservation.")
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         readonly=True,
                                         states={'draft':
                                                 [('readonly', False)]},
                                         help="Invoice address for "
                                         "current reservation.")
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       readonly=True,
                                       states={'draft':
                                               [('readonly', False)]},
                                       help="The name and address of the "
                                       "contact that requested the order "
                                       "or quotation.")
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          readonly=True,
                                          states={'draft':
                                                  [('readonly', False)]},
                                          help="Delivery address"
                                          "for current reservation. ")
    checkin = fields.Datetime('Expected Start Date', required=True,
                              readonly=True,
                              states={'draft': [('readonly', False)]})
    checkout = fields.Datetime('Expected End Date', required=True,
                               readonly=True,
                               states={'draft': [('readonly', False)]})
    reservation_line = fields.One2many('asset_reservation.line', 'line_id',
                                       'Reservation Line',
                                       help='Asset reservation details.',
                                       readonly=True,
                                       states={'draft': [('readonly', False)]},
                                       )
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ('done', 'Done')],
                             'State', readonly=True,
                             default=lambda *a: 'draft')
    dummy = fields.Datetime('Dummy')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for reserv_rec in self:
            if reserv_rec.state != 'draft':
                raise ValidationError(_('You cannot delete Reservation in %s\
                                         state.') % (reserv_rec.state))
        return super(AssetReservation, self).unlink()

    @api.multi
    def copy(self):
        ctx = dict(self._context) or {}
        ctx.update({'duplicate': True})
        return super(AssetReservation, self.with_context(ctx)).copy()

    @api.constrains('checkin', 'checkout')
    def check_in_out_dates(self):
        """
        When date_order is less then check-in date or
        Checkout date should be greater than the check-in date.
        """
        if self.checkout and self.checkin:
            if self.checkin < self.date_order:
                raise ValidationError(_('Start date should be greater than \
                                         the current date.'))
            if self.checkout < self.checkin:
                raise ValidationError(_('End date should be greater \
                                         than Start date.'))

    @api.model
    def _needaction_count(self, domain=None):
        """
         Show a count of draft state reservations on the menu badge.
         """
        return self.search_count([('state', '=', 'draft')])

    @api.onchange('checkout', 'checkin')
    def on_change_checkout(self):
        '''
        When you change checkout or checkin update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        checkout_date = time.strftime(dt)
        checkin_date = time.strftime(dt)
        if not (checkout_date and checkin_date):
            return {'value': {}}
        delta = timedelta(days=1)
        dat_a = time.strptime(checkout_date, dt)[:5]
        addDays = datetime(*dat_a) + delta
        self.dummy = addDays.strftime(dt)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the asset reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if not vals:
            vals = {}
        vals['reservation_no'] = self.env['ir.sequence'].\
            next_by_code('asset.reservation') or 'New'
        return super(AssetReservation, self).create(vals)

    @api.multi
    def check_overlap(self, date1, date2):
        date2 = datetime.strptime(date2, '%Y-%m-%d')
        date1 = datetime.strptime(date1, '%Y-%m-%d')
        delta = date2 - date1
        return set([date1 + timedelta(days=i) for i in range(delta.days + 1)])

    @api.multi
    def confirmed_reservation(self):
        """
        This method creates a new record set for asset reservation line
        -------------------------------------------------------------------
        @param self: The object pointer
        @return: new record set for asset reservation line.
        """
        reservation_line_obj = self.env['account.asset.asset.reservation.line']
        vals = {}
        for reservation in self:
            reserv_checkin = datetime.strptime(reservation.checkin, dt)
            reserv_checkout = datetime.strptime(reservation.checkout, dt)
            asset_bool = False
            for line_id in reservation.reservation_line:
                for asset_id in line_id.reserve:
                    if asset_id.asset_reservation_line_ids:
                        for reserv in asset_id.asset_reservation_line_ids.\
                                search([('status', 'in', ('confirm', 'done')),
                                        ('asset_id', '=', asset_id.id)]):
                            check_in = datetime.strptime(reserv.check_in, dt)
                            check_out = datetime.strptime(reserv.check_out, dt)
                            if check_in <= reserv_checkin <= check_out:
                                asset_bool = True
                            if check_in <= reserv_checkout <= check_out:
                                asset_bool = True
                            if reserv_checkin <= check_in and \
                                    reserv_checkout >= check_out:
                                asset_bool = True
                            mytime = "%Y-%m-%d"
                            r_checkin = datetime.strptime(reservation.checkin,
                                                          dt).date()
                            r_checkin = r_checkin.strftime(mytime)
                            r_checkout = datetime.\
                                strptime(reservation.checkout, dt).date()
                            r_checkout = r_checkout.strftime(mytime)
                            check_intm = datetime.strptime(reserv.check_in,
                                                           dt).date()
                            check_outtm = datetime.strptime(reserv.check_out,
                                                            dt).date()
                            check_intm = check_intm.strftime(mytime)
                            check_outtm = check_outtm.strftime(mytime)
                            range1 = [r_checkin, r_checkout]
                            range2 = [check_intm, check_outtm]
                            overlap_dates = self.check_overlap(*range1) \
                                & self.check_overlap(*range2)
                            overlap_dates = [datetime.strftime(dates,
                                                               '%d/%m/%Y') for
                                             dates in overlap_dates]
                            if asset_bool:
                                raise ValidationError(_('You tried to Confirm '
                                                        'Reservation with asset'
                                                        ' those already '
                                                        'reserved in this '
                                                        'Reservation Period. '
                                                        'Overlap Dates are '
                                                        '%s') % overlap_dates)
                            else:
                                self.state = 'confirm'
                                vals = {'asset_id': asset_id.id,
                                        'check_in': reservation.checkin,
                                        'check_out': reservation.checkout,
                                        'state': 'assigned',
                                        'reservation_id': reservation.id,
                                        }
                                asset_id.write({'is_rental': False,
                                               'rental_status': 'rented'})
                        else:
                            self.state = 'confirm'
                            vals = {'asset_id': asset_id.id,
                                    'check_in': reservation.checkin,
                                    'check_out': reservation.checkout,
                                    'state': 'assigned',
                                    'reservation_id': reservation.id,
                                    }
                            asset_id.write({'is_rental': False,
                                           'rental_status': 'rented'})
                    else:
                        self.state = 'confirm'
                        vals = {'asset_id': asset_id.id,
                                'check_in': reservation.checkin,
                                'check_out': reservation.checkout,
                                'state': 'assigned',
                                'reservation_id': reservation.id,
                                }
                        asset_id.write({'is_rental': False,
                                       'rental_status': 'rented'})
                    reservation_line_obj.create(vals)
        return True

    @api.multi
    def cancel_reservation(self):
        """
        This method cancel record set for asset reservation line
        ------------------------------------------------------------------
        @param self: The object pointer
        @return: cancel record set for asset asset reservation line.
        """
        account_asset_res_line_obj = self.env['account.asset.asset.reservation.line']
        asset_res_line_obj = self.env['asset_reservation.line']
        self.state = 'cancel'
        if self.sale_order_id:
            self.sale_order_id.action_cancel()
        asset_reservation_line = account_asset_res_line_obj.search([('reservation_id',
                                                           'in', self.ids)])
        asset_reservation_line.write({'state': 'unassigned'})
        asset_reservation_line.unlink()
        reservation_lines = asset_res_line_obj.search([('line_id',
                                                        'in', self.ids)])
        for reservation_line in reservation_lines:
            reservation_line.reserve.write({'is_rental': True,
                                            'rental_status': 'available'})
        return True

    @api.multi
    def set_to_draft_reservation(self):
        self.state = 'draft'
        return True

    @api.multi
    def create_sales(self):
        """
        This method creates a new sale order.
        -----------------------------------------
        @param self: The object pointer
        @return: new record set for sales order.
        """
        sale_order_obj = self.env['sale.order']
        asset_obj = self.env['account.asset.asset']
        for reservation in self:
            so_lines = []
            checkin_date = reservation['checkin']
            checkout_date = reservation['checkout']
            if not self.checkin < self.checkout:
                raise ValidationError(_('End date should be greater \
                                             than the Start date.'))
            duration_vals = (self.onchange_check_dates
                             (checkin_date=checkin_date,
                              checkout_date=checkout_date, duration=False))
            duration = duration_vals.get('duration') or 0.0
            sale_order_vals = {
                'date_order': reservation.date_order,
                #'warehouse_id': reservation.warehouse_id.id,
                'partner_id': reservation.partner_id.id,
                'pricelist_id': reservation.pricelist_id.id,
                'partner_invoice_id': reservation.partner_invoice_id.id,
                'partner_shipping_id': reservation.partner_shipping_id.id,
                #'checkin_date': reservation.checkin,
                #'checkout_date': reservation.checkout,
                #'duration': duration,
                'reservation_id': reservation.id,
                #'service_lines': reservation['id']
            }
            for line in reservation.reservation_line:
                for r in line.reserve:
                    so_lines.append((0, 0, {
                        'rental': True,
                        'start_date': checkin_date,
                        'end_date': checkout_date,
                        'product_id': r.product_id and r.product_id.id or False,
                        'name': reservation['reservation_no'],
                        'price_unit': r.product_id and r.product_id.list_price or 0,
                        'number_of_days': duration,
                        'rental_type': 'new_rental',
                        'rental_qty': 1,
                        'product_uom_qty': duration,
                        #'is_reserved': True,
                    }))
                    res_obj = asset_obj.browse([r.id])
                    res_obj.write({'rental_status': 'rented', 's_rental': False})
            sale_order_vals.update({'order_line': so_lines})
            so = sale_order_obj.create(sale_order_vals)
            if so:
                self.sale_order_id = so.id
                for rm_line in so.order_line:
                    rm_line.product_id_change()
            #self._cr.execute('insert into _reservation_rel'
            #                 '(order_id, invoice_id) values (%s,%s)',
            #                 (reservation.id, so.id))
            self.state = 'done'
        return True

    @api.multi
    def action_view_sales_order(self):
        if self.sale_order_id:
            return {
                'name': _('Sales Order'),
                'view_mode': 'form',
                'view_id': self.env.ref('sale.view_order_form').id,
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'res_id': self.sale_order_id.id,
            }

    @api.one
    def send_reservation_mail(self):
        '''
        This function opens a window to compose an email,
        template message loaded by default.
        @param self: object pointer
        '''
        assert len(self._ids) == 1, 'This is for a single id at a time.'
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = (ir_model_data.get_object_reference
                           ('asset_reservations',
                            'mail_template_asset_reservation')[1])
        except ValueError:
            template_id = False
        try:
            compose_form_id = (ir_model_data.get_object_reference
                               ('mail',
                                'email_compose_message_wizard_form')[1])
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'asset.reservation',
            'default_res_id': self._ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_send': True,
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
            'force_send': True
        }

    @api.model
    def reservation_reminder_24hrs(self):
        """
        This method is for scheduler
        every 1day scheduler will call this method to
        find all tomorrow's reservations.
        ----------------------------------------------
        @param self: The object pointer
        @return: send a mail
        """
        now_str = time.strftime(dt)
        now_date = datetime.strptime(now_str, dt)
        ir_model_data = self.env['ir.model.data']
        template_id = (ir_model_data.get_object_reference
                       ('asset_reservations',
                        'mail_template_reservation_reminder_24hrs')[1])
        template_rec = self.env['mail.template'].browse(template_id)
        for reserv_rec in self.search([]):
            checkin_date = (datetime.strptime(reserv_rec.checkin, dt))
            difference = relativedelta(now_date, checkin_date)
            if(difference.days == -1 and reserv_rec.partner_id.email and
               reserv_rec.state == 'confirm'):
                template_rec.send_mail(reserv_rec.id, force_send=True)
        return True

    @api.multi
    def onchange_check_dates(self, checkin_date=False, checkout_date=False,
                             duration=False):
        '''
        This method gives the duration between check in checkout if
        customer will leave only for some hour it would be considers
        as a whole day. If customer will checkin checkout for more or equal
        hours, which configured in company as additional hours than it would
        be consider as full days
        --------------------------------------------------------------------
        @param self: object pointer
        @return: Duration and checkout_date
        '''
        value = {}
        configured_addition_hours = 0
        wc_id = 0 #self.warehouse_id
        whcomp_id = wc_id #or wc_id.company_id
        if whcomp_id:
            configured_addition_hours = wc_id.company_id.additional_hours
        duration = 0
        if checkin_date and checkout_date:
            chkin_dt = datetime.strptime(checkin_date, dt)
            chkout_dt = datetime.strptime(checkout_date, dt)
            dur = chkout_dt - chkin_dt
            duration = dur.days + 1
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60))
                if additional_hours <= abs(configured_addition_hours * 60):
                    duration -= 1
        value.update({'duration': duration})
        return value


class AccountAssetAssetReservationLine(models.Model):

    _name = 'account.asset.asset.reservation.line'
    _description = 'Asset Asset Reservation'
    _rec_name = 'asset_id'

    asset_id = fields.Many2one('account.asset.asset', string='Asset')
    check_in = fields.Datetime('Check In Date', required=True)
    check_out = fields.Datetime('Check Out Date', required=True)
    state = fields.Selection([('assigned', 'Assigned'),
                              ('unassigned', 'Unassigned')], 'Asset Status')
    reservation_id = fields.Many2one('asset.reservation',
                                     string='Reservation')
    status = fields.Selection(string='state', related='reservation_id.state')


class AccountAssetAsset(models.Model):

    _inherit = 'account.asset.asset'

    is_rental = fields.Boolean(string='Is Available For Rental', default=True)
    asset_reservation_line_ids = fields.One2many('account.asset.asset.reservation.line',
                                                'asset_id',
                                                string='Asset Reserve Line')

    product_id = fields.Many2one('product.product', 'Product',
                                 required=True, #delegate=True,
                                 domain=[('rented_product_id', '!=', False)],
                                 ondelete='cascade')
    rental_status = fields.Selection([('available', 'Available'),
                               ('rented', 'Rented')],
                              'Rental Status', default='available')
    color = fields.Integer(string='Color Index')
    hide_asset_depreciation_fields = fields.Boolean(related="company_id.hide_asset_depreciation_fields", string='Hide depreciation fields on assets form')

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for asset in self:
            for reserv_line in asset.asset_reservation_line_ids:
                if reserv_line.status == 'confirm':
                    raise ValidationError(_('User is not able to delete the \
                                            asset after the asset in %s state \
                                            in reservation')
                                          % (reserv_line.status))
        return super(AccountAssetAsset, self).unlink()

    @api.model
    def cron_asset_line(self):
        """
        This method is for scheduler
        every 1min scheduler will call this method and check Status of
        asset is rented or available
        --------------------------------------------------------------
        @param self: The object pointer
        @return: update status of asset asset reservation line
        """
        reservation_line_obj = self.env['account.asset.asset.reservation.line']
        now = datetime.now()
        curr_date = now.strftime(dt)
        for asset in self.search([]):
            reserv_line_ids = [reservation_line.ids for
                               reservation_line in
                               asset.asset_reservation_line_ids]
            reserv_args = [('id', 'in', reserv_line_ids),
                           ('check_in', '<=', curr_date),
                           ('check_out', '>=', curr_date)]
            reservation_line_ids = reservation_line_obj.search(reserv_args)
            status = {'is_rental': True, 'color': 5}
            if reservation_line_ids.ids:
                status = {'is_rental': False, 'color': 2}
            asset.write(status)
            asset.write(status)
            #if reservation_line_ids.ids:
            #    raise ValidationError(_('Please Check Assets Status \
            #                             for %s.' % (asset.name)))
        return True

    @api.onchange('is_rental')
    def is_rental_change(self):
        '''
        Based on is_rental, status will be updated.
        ----------------------------------------
        @param self: object pointer
        '''
        if self.is_rental is False:
            self.rental_status = 'rented'
        if self.is_rental is True:
            self.rental_status = 'available'

    @api.multi
    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if 'is_rental' in vals and vals['is_rental'] is False:
            vals.update({'color': 2, 'rental_status': 'rented'})
        if 'is_rental'in vals and vals['is_rental'] is True:
            vals.update({'color': 5, 'rental_status': 'available'})
        ret_val = super(AccountAssetAsset, self).write(vals)
        return ret_val

    @api.multi
    def set_asset_status_rented(self):
        """
        This method is used to change the state
        to rented of the asset.
        ---------------------------------------
        @param self: object pointer
        """
        return self.write({'is_rental': False, 'color': 2})

    @api.multi
    def set_asset_status_available(self):
        """
        This method is used to change the state
        to available of the asset.
        ---------------------------------------
        @param self: object pointer
        """
        return self.write({'is_rental': True, 'color': 5})


class AssetReservationLine(models.Model):

    _name = "asset_reservation.line"
    _description = "Reservation Line"

    @api.model
    def _default_category(self):
        res = self.env['account.asset.category'].search([('active', '=', True)], order='name', limit=1)
        return res and res[0] or False

    name = fields.Char('Name', size=64)
    line_id = fields.Many2one('asset.reservation')
    reserve = fields.Many2many('account.asset.asset',
                               'asset_reservation_line_asset_rel',
                               'asset_reservation_line_id', 'asset_id',
                               domain="[('is_rental','=',True),\
                               ('category_id','=',category_id)]")
    category_id = fields.Many2one('account.asset.category', 'Asset Category', default=_default_category)

    @api.onchange('category_id')
    def on_change_categ(self):
        '''
        When you change category_id it check checkin and checkout are
        filled or not if not then raise warning
        -----------------------------------------------------------
        @param self: object pointer
        '''
        account_asset_obj = self.env['account.asset.asset']
        asset_asset_ids = account_asset_obj.search([('category_id', '=',
                                                 self.category_id.id)])
        asset_ids = []
        if not self.line_id.checkin:
            raise ValidationError(_('Before choosing an asset,\n You have to \
                                     select a Check in date or a Check out \
                                     date in the reservation form.'))
        for asset in asset_asset_ids:
            assigned = False
            for line in asset.asset_reservation_line_ids:
                if line.status != 'cancel':
                    if(self.line_id.checkin <= line.check_in <=
                        self.line_id.checkout) or (self.line_id.checkin <=
                                                   line.check_out <=
                                                   self.line_id.checkout):
                        assigned = True
                    elif(line.check_in <= self.line_id.checkin <=
                         line.check_out) or (line.check_in <=
                                             self.line_id.checkout <=
                                             line.check_out):
                        assigned = True
            if not assigned:
                asset_ids.append(asset.id)
        domain = {'reserve': [('id', 'in', asset_ids)]}
        return {'domain': domain}

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        account_asset_reserv_line_obj = self.env['account.asset.asset.reservation.line']
        for reserv_rec in self:
            for rec in reserv_rec.reserve:
                hres_arg = [('asset_id', '=', rec.id),
                            ('reservation_id', '=', reserv_rec.line_id.id)]
                myobj = account_asset_reserv_line_obj.search(hres_arg)
                if myobj.ids:
                    rec.write({'is_rental': True, 'rental_status': 'available'})
                    myobj.unlink()
        return super(AssetReservationLine, self).unlink()


class AssetReservationSummary(models.Model):

    _name = 'asset.reservation.summary'
    _description = 'Asset reservation summary'

    name = fields.Char('Reservation Summary', default='Reservations Summary',
                       invisible=True)
    date_from = fields.Datetime('Date From')
    date_to = fields.Datetime('Date To')
    summary_header = fields.Text('Summary Header')
    asset_summary = fields.Text('Asset Summary')

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(AssetReservationSummary, self).default_get(fields)
        # Added default datetime as today and date to as today + 30.
        from_dt = datetime.today()
        dt_from = from_dt.strftime(dt)
        to_dt = from_dt + relativedelta(days=30)
        dt_to = to_dt.strftime(dt)
        res.update({'date_from': dt_from, 'date_to': dt_to})

        if not self.date_from and self.date_to:
            date_today = datetime.datetime.today()
            first_day = datetime.datetime(date_today.year,
                                          date_today.month, 1, 0, 0, 0)
            first_temp_day = first_day + relativedelta(months=1)
            last_temp_day = first_temp_day - relativedelta(days=1)
            last_day = datetime.datetime(last_temp_day.year,
                                         last_temp_day.month,
                                         last_temp_day.day, 23, 59, 59)
            date_froms = first_day.strftime(dt)
            date_ends = last_day.strftime(dt)
            res.update({'date_from': date_froms, 'date_to': date_ends})
        return res

    @api.multi
    def asset_reservation(self):
        '''
        @param self: object pointer
        '''
        mod_obj = self.env['ir.model.data']
        if self._context is None:
            self._context = {}
        model_data_ids = mod_obj.search([('model', '=', 'ir.ui.view'),
                                         ('name', '=',
                                          'view_asset_reservation_form')])
        resource_id = model_data_ids.read(fields=['res_id'])[0]['res_id']
        return {'name': _('Reconcile Write-Off'),
                'context': self._context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'asset.reservation',
                'views': [(resource_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                }

    @api.onchange('date_from', 'date_to')
    def get_asset_summary(self):
        '''
        @param self: object pointer
         '''
        res = {}
        all_detail = []
        asset_obj = self.env['account.asset.asset']
        reservation_line_obj = self.env['account.asset.asset.reservation.line']
        user_obj = self.env['res.users']
        date_range_list = []
        main_header = []
        summary_header_list = ['Assets']
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_('Please Check Time period Date From can\'t \
                                   be greater than Date To !'))
            if self._context.get('tz', False):
                timezone = pytz.timezone(self._context.get('tz', False))
            else:
                timezone = pytz.timezone('UTC')
            d_frm_obj = datetime.strptime(self.date_from, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            d_to_obj = datetime.strptime(self.date_to, dt)\
                .replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            temp_date = d_frm_obj
            while(temp_date <= d_to_obj):
                val = ''
                val = (str(temp_date.strftime("%a")) + ' ' +
                       str(temp_date.strftime("%b")) + ' ' +
                       str(temp_date.strftime("%d")))
                summary_header_list.append(val)
                date_range_list.append(temp_date.strftime
                                       (dt))
                temp_date = temp_date + timedelta(days=1)
            all_detail.append(summary_header_list)
            asset_ids = asset_obj.search([])
            all_asset_detail = []
            for asset in asset_ids:
                asset_detail = {}
                asset_list_stats = []
                asset_detail.update({'name': asset.name or ''})
                if not asset.asset_reservation_line_ids:
                    for chk_date in date_range_list:
                        asset_list_stats.append({'state': 'Free',
                                                'date': chk_date,
                                                'asset_id': asset.id})
                else:
                    for chk_date in date_range_list:
                        ch_dt = chk_date[:10] + ' 23:59:59'
                        ttime = datetime.strptime(ch_dt, dt)
                        c = ttime.replace(tzinfo=timezone).\
                            astimezone(pytz.timezone('UTC'))
                        chk_date = c.strftime(dt)
                        reserline_ids = asset.asset_reservation_line_ids.ids
                        reservline_ids = (reservation_line_obj.search
                                          ([('id', 'in', reserline_ids),
                                            ('check_in', '<=', chk_date),
                                            ('check_out', '>=', chk_date),
                                            ('state', '=', 'assigned')
                                            ]))
                        if not reservline_ids:
                            sdt = dt
                            chk_date = datetime.strptime(chk_date, sdt)
                            chk_date = datetime.\
                                strftime(chk_date - timedelta(days=1), sdt)
                            reservline_ids = (reservation_line_obj.search
                                              ([('id', 'in', reserline_ids),
                                                ('check_in', '<=', chk_date),
                                                ('check_out', '>=', chk_date),
                                                ('state', '=', 'assigned')]))
                            for res_asset in reservline_ids:
                                rrci = res_asset.check_in
                                rrco = res_asset.check_out
                                cid = datetime.strptime(rrci, dt)
                                cod = datetime.strptime(rrco, dt)
                                dur = cod - cid
                                if asset_list_stats:
                                    count = 0
                                    for rlist in asset_list_stats:
                                        cidst = datetime.strftime(cid, dt)
                                        codst = datetime.strftime(cod, dt)
                                        rm_id = res_asset.asset_id.id
                                        ci = rlist.get('date') >= cidst
                                        co = rlist.get('date') <= codst
                                        rm = rlist.get('asset_id') == rm_id
                                        st = rlist.get('state') == 'Reserved'
                                        if ci and co and rm and st:
                                            count += 1
                                    if count - dur.days == 0:
                                        c_id1 = user_obj.browse(self._uid)
                                        c_id = c_id1.company_id
                                        con_add = 0
                                        amin = 0.0
                                        if c_id:
                                            con_add = c_id.additional_hours
#                                        When configured_addition_hours is
#                                        greater than zero then we calculate
#                                        additional minutes
                                        if con_add > 0:
                                            amin = abs(con_add * 60)
                                        hr_dur = abs((dur.seconds / 60))
#                                        When additional minutes is greater
#                                        than zero then check duration with
#                                        extra minutes and give the asset
#                                        reservation status is reserved or
#                                        free
                                        if amin > 0:
                                            if hr_dur >= amin:
                                                reservline_ids = True
                                            else:
                                                reservline_ids = False
                                        else:
                                            if hr_dur > 0:
                                                reservline_ids = True
                                            else:
                                                reservline_ids = False
                                    else:
                                        reservline_ids = False
                        if reservline_ids:
                            asset_list_stats.append({'state': 'Reserved',
                                                    'date': chk_date,
                                                    'asset_id': asset.id,
                                                    'is_draft': 'No',
                                                    'data_model': '',
                                                    'data_id': 0})
                        else:
                            asset_list_stats.append({'state': 'Free',
                                                    'date': chk_date,
                                                    'asset_id': asset.id})

                asset_detail.update({'value': asset_list_stats})
                all_asset_detail.append(asset_detail)
            main_header.append({'header': summary_header_list})
            self.summary_header = str(main_header)
            self.asset_summary = str(all_asset_detail)
        return res


class QuickAssetReservation(models.TransientModel):
    _name = 'quick.asset.reservation'
    _description = 'Quick Asset Reservation'

    partner_id = fields.Many2one('res.partner', string="Customer",
                                 required=True)
    check_in = fields.Datetime('Start Date', required=True)
    check_out = fields.Datetime('End Date', required=True)
    asset_id = fields.Many2one('account.asset.asset', 'Asset', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'pricelist')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
                                         required=True)
    partner_order_id = fields.Many2one('res.partner', 'Ordering Contact',
                                       required=True)
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
                                          required=True)

    @api.onchange('check_out', 'check_in')
    def on_change_check_out(self):
        '''
        When you change checkout or checkin it will check whether
        Checkout date should be greater than Checkin date
        and update dummy field
        -----------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.check_out and self.check_in:
            if self.check_out < self.check_in:
                raise ValidationError(_('End date should be greater \
                                         than Start date.'))

    @api.onchange('partner_id')
    def onchange_partner_id_res(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the asset reservation as well
        ---------------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice',
                                                'contact'])
            self.partner_invoice_id = addr['invoice']
            self.partner_order_id = addr['contact']
            self.partner_shipping_id = addr['delivery']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(QuickAssetReservation, self).default_get(fields)
        if self._context:
            keys = self._context.keys()
            if 'date' in keys:
                start_date = self._context['date']
                start_date = start_date[:10] + ' 07:00:00'
                res.update({'check_in': start_date})
                checkin_date = (datetime.strptime(start_date, dt))
                to_dt = checkin_date + relativedelta(days=1)
                dt_to = to_dt.strftime(dt)
                if dt_to: res.update({'check_out': dt_to})
            if 'asset_id' in keys:
                asset_id = self._context['asset_id']
                res.update({'asset_id': int(asset_id)})
        return res

    @api.multi
    def asset_reserve(self):
        """
        This method create a new record for asset.reservation
        -----------------------------------------------------
        @param self: The object pointer
        @return: new record set for asset reservation.
        """
        asset_res_obj = self.env['asset.reservation']
        for res in self:
            rec = (asset_res_obj.create
                   ({'partner_id': res.partner_id.id,
                     'partner_invoice_id': res.partner_invoice_id.id,
                     'partner_order_id': res.partner_order_id.id,
                     'partner_shipping_id': res.partner_shipping_id.id,
                     'checkin': res.check_in,
                     'checkout': res.check_out,
                     'pricelist_id': res.pricelist_id.id,
                     'reservation_line': [(0, 0,
                                           {'reserve': [(6, 0,
                                                         [res.asset_id.id])],
                                            'name': (res.asset_id and
                                                     res.asset_id.name or '')
                                            })]
                     }))
        return rec


class ResCompany(models.Model):

    _inherit = 'res.company'

    additional_hours = fields.Integer('Additional Hours',
                                      help="Provide the min hours value for \
                                      check in, checkout days, whatever the \
                                      hours will be provided here based \
                                      on that extra days will be calculated.")


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    reservation_id = fields.Many2one('asset.reservation', string='Reservation')