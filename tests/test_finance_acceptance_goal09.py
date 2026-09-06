import unittest,tempfile
from pathlib import Path
from decimal import Decimal
from hermes_attention.finance import reconcile,FinanceWorkspace
class FinancialHoldoutTest(unittest.TestCase):
 def row(self,value,category='income',account='A',currency='PKR',source_row='1',**kw):return {'date':'2026-06-10','amount':value,'category':category,'account':account,'currency':currency,'source':'statement','source_row':source_row,'description':'Synthetic',**kw}
 def run_rows(self,rows,**kw):return reconcile(rows,period_start='2026-06-01',period_end='2026-06-30',**kw)
 def test_customer_paid_refund_and_expense_received_refund_have_opposite_signs(self):
  common=[self.row('100'),self.row('-2','fee',source_row='2')]
  paid=self.run_rows(common+[self.row('-5','customer_refund',source_row='3')]);received=self.run_rows(common+[self.row('5','expense_refund',source_row='3')])
  self.assertEqual(paid['totals_by_currency']['PKR']['net_cash_flow'],'93');self.assertEqual(received['totals_by_currency']['PKR']['net_cash_flow'],'103')
  ambiguous=self.run_rows(common+[self.row('5','refund',source_row='3')]);self.assertFalse(ambiguous['classification_complete']);self.assertTrue(ambiguous['totals_provisional'])
  wrong=self.run_rows([self.row('5','customer_refund')]);self.assertTrue(any('Sign/category' in q for q in wrong['questions']))
 def test_account_currency_coverage_and_contiguous_statement_union(self):
  rows=[self.row('10'),self.row('1',currency='USD',source_row='2')]
  coverage=[{'account':'A','currency':'PKR','start':'2026-06-01','end':'2026-06-15'},{'account':'A','currency':'PKR','start':'2026-06-16','end':'2026-06-30'}]
  r=self.run_rows(rows,expected_accounts=['A'],coverage=coverage)
  self.assertFalse(r['coverage_complete']);self.assertEqual(r['missing_account_currencies'],[{'account':'A','currency':'USD'}])
  coverage.append({'account':'A','currency':'USD','start':'2026-06-01','end':'2026-06-30'})
  self.assertTrue(self.run_rows(rows,expected_accounts=['A'],coverage=coverage)['coverage_complete'])
  coverage[1]['start']='2026-06-17';self.assertFalse(self.run_rows(rows,expected_accounts=['A'],coverage=coverage)['coverage_complete'])
 def test_cross_currency_transfer_and_conflicting_fx_never_invent_matching_or_conversion(self):
  rows=[self.row('-100','transfer',currency='USD',transfer_id='fx'),self.row('28000','transfer',account='B',source_row='2',transfer_id='fx')]
  rates=[{'from':'USD','to':'PKR','date':'2026-06-10','rate':'280','source':'synthetic assumption'},{'from':'USD','to':'PKR','date':'2026-06-10','rate':'290','source':'contradicting assumption'}]
  r=self.run_rows(rows,base_currency='PKR',fx_rates=rates)
  self.assertEqual(len(r['unmatched_transfers']),1);self.assertFalse(r['classification_complete']);self.assertEqual(len(r['converted_rows']),1)
  self.assertTrue(any('Conflicting dated FX' in q for q in r['questions']))
 def test_large_supported_decimal_sums_do_not_round_in_default_context(self):
  rows=[self.row('999999999999999999.12345678',source_row=str(i)) for i in range(20)]
  r=self.run_rows(rows)
  self.assertEqual(r['totals_by_currency']['PKR']['net_cash_flow'],'19999999999999999982.46913560')
 def test_xlsx_preserves_high_precision_and_source_mapping_as_editable_data(self):
  from hermes_attention.documents import DocumentWorkspace
  from openpyxl import load_workbook
  with tempfile.TemporaryDirectory() as directory:
   docs=DocumentWorkspace(Path(directory).resolve())
   record=docs.generate(conversation_id='fixture',format='xlsx',title='Exact decimals',tables=[{'name':'Amounts','headers':['Value'],'rows':[[Decimal('999999999999999999.12345678')],[Decimal('12.34')]]}])
   book=load_workbook(docs.path(record['id'],'fixture'))
   self.assertEqual(book.active['A2'].value,'999999999999999999.12345678');self.assertEqual(book.active['A2'].data_type,'s')
   self.assertEqual(Decimal(str(book.active['A3'].value)),Decimal('12.34'));self.assertNotEqual(book.active['A3'].data_type,'f')

if __name__=='__main__':unittest.main()

class FinanceInputShapeTests(unittest.TestCase):
 def test_coverage_status_map_returns_actionable_error_without_invented_ranges(self):
  with self.assertRaisesRegex(ValueError,'coverage must be a list'):
   reconcile([],period_start='2026-06-01',period_end='2026-06-30',coverage={'A':'complete'})
  result=reconcile([],period_start='2026-06-01',period_end='2026-06-30',expected_accounts=['A'],coverage=[])
  self.assertFalse(result['coverage_complete']);self.assertIn('A',result['missing_accounts'])
