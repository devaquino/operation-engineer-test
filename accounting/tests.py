#!/user/bin/env python2.7

import unittest
from datetime import date

from accounting import db
from models import Contact, Invoice, Payment, Policy
from utils import PolicyAccounting

"""
#######################################################
Test Suite for Accounting
#######################################################
"""


class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)

    def test_monthly_on_eff_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[0].bill_date, amount=100))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[0].bill_date), 0)

    def test_monthly_on_sixth_installment_bill_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date).all()
        for i in range(0, 6):
            self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                                 date_cursor=invoices[i].bill_date, amount=100))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[11].bill_date), 600)

    def test_monthly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date).all()
        for i in range(0, 12):
            self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                                 date_cursor=invoices[i].bill_date, amount=100))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[11].bill_date), 0)

    def test_two_pay_on_first_installment_bill_date(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
            .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[0].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 600)

    def test_two_pay_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
            .order_by(Invoice.bill_date).all()
        for i in range(1, 3):
            self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                                 date_cursor=invoices[0].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)

class TestCancellations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_evaluate_cancellation_pending_on_cancel_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 2, 15)), True)

    def test_evaluate_cancellation_pending_before_due_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 1, 14)), False)

    def test_evaluate_cancellation_pending_on_due_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 1, 15)), False)

    def test_evaluate_cancellation_pending_after_due_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy)
        self.assertEquals(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 1, 17)), False)

class TestChangeBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_deleted_invoices_changed_billing_schedule_from_quaterly(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy)
        pa.change_billing_schedule("Monthly")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.deleted.is_(True))\
                                .all()
        self.assertEquals(len(invoices), 4)

    def test_deleted_invoices_changed_billing_schedule_from_monthly(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy)
        pa.change_billing_schedule("Quarterly")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.deleted.is_(True))\
                                .all()
        self.assertEquals(len(invoices), 12)

    def test_deleted_invoices_changed_billing_schedule_from_two_pay(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy)
        pa.change_billing_schedule("Quarterly")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
                                .filter(Invoice.deleted.is_(True)) \
                                .all()
        self.assertEquals(len(invoices), 2)

    def test_new_invoices_changed_billing_schedule_from_quaterly(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy)
        pa.change_billing_schedule("Monthly")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
            .filter(Invoice.deleted.is_(False)) \
            .all()
        self.assertEquals(len(invoices), 12)


    def test_new_invoices_changed_billing_schedule_from_monthly(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy)
        pa.change_billing_schedule("Quarterly")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.deleted.is_(False))\
                                .all()
        self.assertEquals(len(invoices), 4)

    def test_new_invoices_changed_billing_schedule_from_two_pay(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy)
        pa.change_billing_schedule("Two-Pay")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id) \
                                .filter(Invoice.deleted.is_(False)) \
                                .all()
        self.assertEquals(len(invoices), 2)


