# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta

class TimeDependent(models.AbstractModel):
    _name = 'time.dependent'

    @api.multi
    def track_changes(self, rec, values, time_dependent_model_rec, validation_to):
        tracking_vals = []
        for field in time_dependent_model_rec.field_ids:
            #Capture changes if selected field's value is changed.
            if values.has_key(field.name):
                field_dict = rec.read([field.name])[0]
                if field.ttype == 'boolean':
                    old_value = field_dict.get(field.name, False)
                    new_value = values.get(field.name, False)
                elif field.ttype == 'integer' or field.ttype == 'float':
                    old_value = field_dict.get(field.name) if field_dict.get(field.name, False) else "0"
                    new_value = values.get(field.name) if values.get(field.name, False) else "0"
                elif field.ttype == 'selection':
                    old_value = dict(rec._fields[field.name].selection)[field_dict.get(field.name)] if field_dict.get(field.name, False) else "NA"
                    new_value = dict(rec._fields[field.name].selection)[values.get(field.name)] if values.get(field.name, False) else "NA"
                else:
                    old_value = field_dict.get(field.name) if field_dict.get(field.name, False) else "NA"
                    new_value = values.get(field.name) if values.get(field.name, False) else "NA"
                tracking_vals.append((0, 0, {'field_name': field.field_description, 'old_value': old_value, 'new_value': new_value}))
        if tracking_vals:
            values['date_start'] = date.today() #Update Validity From with today's date
            validity_periods_tracking_vals = [(0, 0, {'validity_from': date.today(), 'validity_to': validation_to, 'tracking_ids': tracking_vals})]
            record = rec.env['time.dependent.record'].search([('rec_id', '=', rec.id), ('model_id', '=', time_dependent_model_rec.id)], limit=1)
            #Create new record with Validity Periods and Tracking Values.
            if not record: time_dependent_model_rec.record_ids = [(0, 0, {'rec_id': rec.id, 'model_id': time_dependent_model_rec.id, 'validity_period_ids': validity_periods_tracking_vals})]
            #Update record with Validity Periods and Tracking Values.
            elif record:
                validity_period_rec = self.env['time.validity.period'].search([('record_id', '=', record.id)], order='id desc', limit=1)
                if not validity_period_rec:
                    record.validity_period_ids = validity_periods_tracking_vals
                elif validity_period_rec:
                    if validity_period_rec.validity_from == date.today().strftime("%Y-%m-%d"):
                        validity_period_rec.tracking_ids = tracking_vals
                        validity_period_rec.validity_to = validation_to
                    elif validity_period_rec.validity_from != date.today().strftime("%Y-%m-%d"):
                        validity_period_rec.validity_to = date.today() - timedelta(days=1)
                        record.validity_period_ids = validity_periods_tracking_vals
        return True

    @api.multi
    def check_validity(self, values):
        for rec in self:
            time_dependent_model_rec = rec.env['time.dependent.model'].search([('model_id.model', '=', rec._name)])
            if time_dependent_model_rec:
                # Check extra filter
                changes_tracking = True
                field = time_dependent_model_rec.field_id
                if field:
                    if rec.read([field.name])[0].get(field.name, False) != time_dependent_model_rec.value:
                        changes_tracking = False
                if changes_tracking:
                    #Check validation period
                    validation_from = values['date_start'] if values.has_key('date_start') else self.date_start
                    validation_to = values['date_end'] if values.has_key('date_end') else self.date_end
                    if validation_from and validation_to:
                        if datetime.strptime(validation_from, "%Y-%m-%d").date() <= date.today() and datetime.strptime(validation_to, "%Y-%m-%d").date() >= date.today():
                            rec.track_changes(rec, values, time_dependent_model_rec, validation_to)
                    elif validation_from:
                        if datetime.strptime(validation_from, "%Y-%m-%d").date() <= date.today():
                            rec.track_changes(rec, values, time_dependent_model_rec, validation_to)
                    elif validation_to:
                        if datetime.strptime(validation_to, "%Y-%m-%d").date() >= date.today():
                            rec.track_changes(rec, values, time_dependent_model_rec, validation_to)
        return True

    @api.multi
    def write(self, values):
        self.check_validity(values)
        return super(TimeDependent, self).write(values)

    @api.multi
    def unlink(self):
        for rec in self:
            time_dependent_model_rec = rec.env['time.dependent.model'].search([('model_id.model', '=', rec._name)])
            if time_dependent_model_rec:
                record = rec.env['time.dependent.record'].search([('rec_id', '=', rec.id), ('model_id', '=', time_dependent_model_rec.id)], limit=1)
                if record: record.unlink()
        return super(TimeDependent, self).unlink()


class TimeDependentModel(models.Model):
    _name = 'time.dependent.model'
    _rec_name = 'model_id'

    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade', required=True, index=True)
    field_ids = fields.Many2many('ir.model.fields', column1='dependent_id', column2='field_id', string='Fields', required=True, index=True)
    field_id = fields.Many2one('ir.model.fields', string='Field to Filter', help="Boolean fields to filter based on time faced tracking is done.")
    value = fields.Boolean(string="Value", default=True, help="Value for selected boolean field to filter based on time faced tracking is done.")
    record_ids = fields.One2many('time.dependent.record', 'model_id', string='Record Ref#')

    # Clear value for field_ids and field_id when model_id is changed
    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_ids = []
        self.field_id = False

    @api.constrains('model_id')
    def _check_model_sequence(self):
        if self.search_count([('model_id', '=', self.model_id.id)]) > 1:
            raise ValidationError(_("Model already exists in time dependent."))


class TimeDependentRecord(models.Model):
    _name = 'time.dependent.record'

    rec_id = fields.Integer(string='Record ID')
    name = fields.Char(string="Record Ref#", compute='_get_record_reference')
    validity_period_ids = fields.One2many('time.validity.period', 'record_id', string='Validity Periods')
    model_id = fields.Many2one('time.dependent.model', string='Model', ondelete='cascade')

    def _get_record_reference(self):
        for record in self:
            model = record.model_id.model_id.model
            refObj =  self.env[model].browse(record.rec_id)
            record.name = refObj.name_get()[0][1] or ''

    @api.multi
    def action_view_reference_record(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].search([('res_model','=',self.model_id.model_id.model)], order='id', limit=1)
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': 'form',
            'view_mode': 'form',
            'target': action.target,
            'res_id': self.rec_id or False,
            'res_model': action.res_model,
            'domain': [('id', '=', self.rec_id)],
        }


class TimeValidityPeriod(models.Model):
    _name = 'time.validity.period'

    validity_from = fields.Date('Validity From')
    validity_to = fields.Date('Validity To')
    record_id = fields.Many2one('time.dependent.record', string='Record', ondelete='cascade')
    tracking_ids = fields.One2many('time.tracking.values', 'validity_period_id', string="Tracking Values")


class TimeTrackingValues(models.Model):
    _name = 'time.tracking.values'
    _rec_name = 'field_name'

    field_name = fields.Char('Field')
    old_value = fields.Char('Old Value')
    new_value = fields.Char('New Value')
    validity_period_id = fields.Many2one('time.validity.period', string='History', ondelete='cascade')