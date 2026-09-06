"""Evidence-bounded financial preparation using fixed Decimal transformations.

No banking transport, tax-rate inference, submission, or arbitrary code execution.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
import hashlib
import json
from pathlib import Path
import re
import uuid
from .documents import DocumentWorkspace, _identifier, _locked, _no_symlinks, _private_write
import os

CATEGORIES = {'income','expense','refund','customer_refund','expense_refund','fee','transfer','asset','liability','unknown'}


def exact_arithmetic(function):
    @wraps(function)
    def call(*args,**kwargs):
        with localcontext() as context:
            context.prec=64
            return function(*args,**kwargs)
    return call


def amount(value):
    if isinstance(value, (float, bool)):
        raise ValueError('Supply decimal amounts as strings, not binary floats')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal amount') from exc
    if not result.is_finite() or abs(result) > Decimal('1e18') or result.as_tuple().exponent < -8:
        raise ValueError('Amount is outside supported precision/range')
    return result


@dataclass(frozen=True)
class Transaction:
    date: str
    amount: str
    currency: str
    account: str
    description: str
    source: str
    category: str = 'unknown'
    transaction_id: str = ''
    transfer_id: str = ''
    source_row: str = ''

    def validated(self):
        date.fromisoformat(self.date)
        amount(self.amount)
        if not re.fullmatch(r'[A-Z]{3}',self.currency) or not self.account or not self.source:
            raise ValueError('Currency, account, and source evidence required')
        if self.category not in CATEGORIES:
            raise ValueError('Unknown transaction category')
        if any(len(str(v)) > 2000 for v in asdict(self).values()):
            raise ValueError('Transaction field limit exceeded')
        return self


def parse_rows(rows, *, mapping, source, account, currency=None):
    """Explicit column mapping prevents guessing debit/credit sign or date locale.

    mapping needs date and either amount or debit/credit. ISO dates are required.
    A caller must normalize bank-specific dates explicitly before this operation.
    """
    result, rejected = [], []
    for i,row in enumerate(rows,2):
        try:
            if 'amount' in mapping:
                value = amount(row[mapping['amount']])
            else:
                debit = amount(row.get(mapping.get('debit'), '') or '0')
                credit = amount(row.get(mapping.get('credit'), '') or '0')
                if debit < 0 or credit < 0: raise ValueError('Debit/credit columns must be nonnegative')
                if debit>0 and credit>0:raise ValueError('Both debit and credit are populated; split or explicitly review this combined row')
                value = credit - debit
            tx = Transaction(date=str(row[mapping['date']]), amount=str(value),currency=str(row.get(mapping.get('currency'),currency) or ''),account=account,description=str(row.get(mapping.get('description'),'')),source=source,category=str(row.get(mapping.get('category'),'unknown')),transaction_id=str(row.get(mapping.get('transaction_id'),'')),transfer_id=str(row.get(mapping.get('transfer_id'),'')),source_row=f'row:{i}').validated()
            result.append(asdict(tx))
        except (ValueError,KeyError,TypeError) as exc:
            rejected.append({'source':source,'row':i,'reason':str(exc)})
    return {'transactions':result,'rejected_rows':rejected,'complete':not rejected}


@exact_arithmetic
def reconcile(transactions, *, period_start, period_end, expected_accounts=(), coverage=(), fx_rates=(), base_currency=None):
    """Dedup only stable bank transaction IDs or exact same source-row references.

    Similar rows without stable identity are retained and flagged, never erased.
    Explicit transfer IDs need opposite signs, accounts, currency, balanced amounts.
    Unmatched transfers remain separately visible, excluded from asserted income.
    """
    if not isinstance(transactions,(list,tuple)) or not all(isinstance(row,dict) for row in transactions):raise ValueError('transactions must be a list of source-bound transaction objects')
    if not isinstance(coverage,(list,tuple)) or not all(isinstance(row,dict) and all(isinstance(row.get(k),str) for k in ('account','currency','start','end')) for row in coverage):raise ValueError('coverage must be a list of objects: account, currency, start and end (YYYY-MM-DD); optional opening_balance, closing_balance, source. Account-to-status mappings are not supported; omit unconfirmed coverage.')
    if not isinstance(fx_rates,(list,tuple)) or not all(isinstance(row,dict) and {'from','to','date','rate','source'}<=set(row) for row in fx_rates):raise ValueError('fx_rates must be a list of dated from/to/rate/source objects; use an empty list when no rate is supported')
    start,end = date.fromisoformat(period_start),date.fromisoformat(period_end)
    if start > end: raise ValueError('Period start follows period end')
    if len(transactions) > 100_000: raise ValueError('Transaction limit exceeded')
    accepted, duplicates, outside, questions, conflicts = [], [], [], [], []
    seen, similarity = {}, {}
    for raw in transactions:
        tx = raw if isinstance(raw,Transaction) else Transaction(**raw)
        tx.validated(); row = asdict(tx)
        if not start <= date.fromisoformat(tx.date) <= end:
            outside.append(row); continue
        key = ('id',tx.account,tx.transaction_id) if tx.transaction_id else ('source',tx.source,tx.source_row) if tx.source_row else None
        semantic = (tx.date, str(amount(tx.amount)), tx.currency, tx.account, tx.description,tx.category,tx.transfer_id)
        if key in seen:
            previous = seen[key]
            prev_semantic = (previous['date'],str(amount(previous['amount'])),previous['currency'],previous['account'],previous['description'],previous['category'],previous['transfer_id'])
            if semantic == prev_semantic:
                duplicates.append({'duplicate':row,'retained':previous}); continue
            conflicts.append({'identity':list(key),'first':previous,'conflict':row})
            questions.append(f'Conflicting records for {tx.account} transaction identity; both retained pending review')
        if key: seen[key] = row
        if semantic in similarity:
            questions.append(f'Possible duplicate retained: {tx.source} {tx.source_row}; matching values are not proof of identity')
        similarity[semantic] = row
        accepted.append(row)
    groups = defaultdict(list)
    for row in accepted:
        if row['transfer_id']: groups[row['transfer_id']].append(row)
    matched, unmatched = [], []
    for identity, rows in groups.items():
        valid = len(rows)==2 and rows[0]['account']!=rows[1]['account'] and rows[0]['currency']==rows[1]['currency'] and sum((amount(r['amount']) for r in rows),Decimal(0))==0 and amount(rows[0]['amount'])!=0
        if valid:
            for row in rows: row['effective_category'] = 'transfer'
            matched.append({'transfer_id':identity,'rows':rows})
        else:
            for row in rows: row['effective_category'] = 'transfer_unreconciled'
            unmatched.append({'transfer_id':identity,'rows':rows})
            questions.append(f'Transfer {identity} is unmatched or requires explicit currency/fee reconciliation')
    totals = defaultdict(lambda:defaultdict(Decimal))
    account_flows = defaultdict(Decimal)
    classification_issues=[]
    for row in accepted:
        currency = row['currency']; value = amount(row['amount']); category = row.get('effective_category',row['category'])
        totals[currency]['net_cash_flow'] += value
        account_flows[(row['account'],currency)] += value
        totals[currency][category] += value
        if category == 'unknown': classification_issues.append(f"Classify {row['source']} {row['source_row']} ({currency} {value})")
        if category == 'refund': classification_issues.append(f"Refund direction/purpose needs review: {row['source']} {row['source_row']}; distinguish customer_refund paid out from expense_refund received")
        if category in {'expense','fee','customer_refund'} and value > 0 or category in {'income','expense_refund'} and value < 0:
            classification_issues.append(f"Sign/category mismatch: {row['source']} {row['source_row']}")
        if category == 'transfer' and not row.get('effective_category'):
            classification_issues.append(f"Unpaired transfer: {row['source']} {row['source_row']}")
    questions.extend(classification_issues)
    balance_checks=[]; covered=set(); covered_pairs=set(); intervals=defaultdict(list)
    for item in coverage:
        account=item['account']; curr=item['currency']
        cstart,cend=date.fromisoformat(item['start']),date.fromisoformat(item['end'])
        if cstart>cend: raise ValueError('Coverage interval start follows end')
        if not re.fullmatch(r'[A-Z]{3}',curr): raise ValueError('Coverage currency must be an ISO currency code')
        intervals[(account,curr)].append((cstart,cend))
        if 'opening_balance' in item and 'closing_balance' in item:
            if start<=cstart<=cend<=end:
                flow=sum((amount(r['amount']) for r in accepted if r['account']==account and r['currency']==curr and cstart<=date.fromisoformat(r['date'])<=cend),Decimal(0))
                expected=amount(item['opening_balance'])+flow
                actual=amount(item['closing_balance'])
                balance_checks.append({'account':account,'currency':curr,'expected_closing':str(expected),'actual_closing':str(actual),'difference':str(actual-expected),'balanced':actual==expected,'source':item.get('source','owner-supplied')})
            else: questions.append(f'Balance check requires matching report period: {account}')
    for pair,spans in intervals.items():
        through=start-timedelta(days=1)
        for a,b in sorted(spans):
            if a>through+timedelta(days=1): break
            through=max(through,b)
        if through>=end: covered_pairs.add(pair); covered.add(pair[0])
        else: questions.append(f'Incomplete period coverage: {pair[0]} {pair[1]}')
    missing_pairs=sorted({(r['account'],r['currency']) for r in accepted}-covered_pairs)
    questions.extend(f'Missing full-period currency records: {a} {c}' for a,c in missing_pairs)
    missing = sorted(set(expected_accounts)-covered)
    questions.extend(f'Missing full-period account records: {a}' for a in missing)
    converted=[]
    if base_currency:
        if not re.fullmatch(r'[A-Z]{3}',base_currency):raise ValueError('Base currency must be an ISO currency code')
        rates={};conflicted_rates=set()
        for rate in fx_rates:
            value=amount(rate['rate']); date.fromisoformat(rate['date'])
            if value<=0 or not rate.get('source'): raise ValueError('FX requires a positive rate, date, and cited source/owner assumption')
            key=(rate['from'],rate['to'],rate['date'])
            if key in rates and amount(rates[key]['rate'])!=value:conflicted_rates.add(key);questions.append(f'Conflicting dated FX rates: {key}')
            rates[key]=rate
        for row in accepted:
            if row['currency']==base_currency: value=amount(row['amount']); rate_info=None
            else:
                rate_info=rates.get((row['currency'],base_currency,row['date']))
                if not rate_info or (row['currency'],base_currency,row['date']) in conflicted_rates:
                    questions.append(f"Missing dated FX rate: {row['currency']} to {base_currency} on {row['date']}"); continue
                value=amount(row['amount'])*amount(rate_info['rate'])
            converted.append({'source':row['source'],'source_row':row['source_row'],'amount':str(value),'currency':base_currency,'rate':rate_info})
    serialized_totals={c:{k:str(v) for k,v in values.items()} for c,values in totals.items()}
    return {'period':{'start':period_start,'end':period_end},'transactions':accepted,'totals_by_currency':serialized_totals,'duplicates':duplicates,'identity_conflicts':conflicts,'outside_period':outside,'matched_transfers':matched,'unmatched_transfers':unmatched,'balance_checks':balance_checks,'missing_accounts':missing,'missing_account_currencies':[{'account':a,'currency':c} for a,c in missing_pairs],'questions':list(dict.fromkeys(questions)),'converted_rows':converted,'coverage_complete':bool(expected_accounts) and not missing and not missing_pairs,'classification_complete':not bool(classification_issues or unmatched or conflicts),'calculation_method':'Decimal; fixed reviewed transformations; no arbitrary code','totals_provisional':bool(questions or conflicts or unmatched or any(not b['balanced'] for b in balance_checks)), 'financial_advice_status':'record preparation; no tax assessment or submission'}


class FinanceWorkspace:
    def __init__(self, root):
        self.root=_no_symlinks(root); self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.documents=DocumentWorkspace(self.root/'documents')
        self.state_path=self.root/'finance.json'

    def _read(self):
        _no_symlinks(self.state_path)
        return json.loads(self.state_path.read_text()) if self.state_path.exists() else {'workspaces':{}}

    def update(self, conversation_id, *, transactions, period_start,period_end,expected_accounts=None,coverage=None,fx_rates=None,base_currency=None,source_selection=None):
        """Append supplied records, then reconcile; prior snapshots remain recoverable."""
        _identifier(conversation_id)
        with _locked(self.root):
            state=self._read(); prior=state['workspaces'].get(conversation_id,{'revisions':[]})
            previous=prior['revisions'][-1] if prior['revisions'] else None
            combined=(previous['input_transactions'] if previous else [])+transactions
            prior_options=previous.get('options',{}) if previous else {}
            options={'expected_accounts':expected_accounts if expected_accounts is not None else prior_options.get('expected_accounts',[]),'coverage':coverage if coverage is not None else prior_options.get('coverage',[]),'fx_rates':fx_rates if fx_rates is not None else prior_options.get('fx_rates',[]),'base_currency':base_currency if base_currency is not None else prior_options.get('base_currency')}
            result=reconcile(combined,period_start=period_start,period_end=period_end,**options)
            if source_selection is not None:
                result['sourceSelection']=source_selection
                if not source_selection['allGrantedCsvSourcesAndRowsIncluded']:
                    result.update(coverage_complete=False,totals_provisional=True,questions=list(dict.fromkeys(result['questions']+['Selected transactions omit or cannot attest some granted CSV sources/rows; totals cover only the selected parsed records.'])))
            revision={'options':options,'id':'fin_'+uuid.uuid4().hex,'version':len(prior['revisions'])+1,'input_transactions':combined,'result':result}
            prior['revisions'].append(revision); state['workspaces'][conversation_id]=prior
            temporary=self.root/('.finance-'+uuid.uuid4().hex)
            _private_write(temporary,json.dumps(state).encode()); os.replace(temporary,self.state_path)
            return revision

    def get(self,conversation_id):
        _identifier(conversation_id)
        return self._read()['workspaces'].get(conversation_id,{'revisions':[]})

    def deliver(self,conversation_id, *, reconciliation, title='Financial record reconciliation',source_ids=(),parent_ids=None,turn_id='',review_status='not_reviewed'):
        rows=[[c,k.replace('_',' ').capitalize(),Decimal(v)] for c,values in reconciliation['totals_by_currency'].items() for k,v in values.items()]
        summary={'name':'Summary','headers':['Currency','Category','Amount'],'rows':rows}
        transactions={'name':'Transactions','headers':['Date','Account','Currency','Amount','Category','Description','Source','Row'],'rows':[[r['date'],r['account'],r['currency'],amount(r['amount']),r.get('effective_category',r['category']),r['description'],r['source'],r['source_row']] for r in reconciliation['transactions']]}
        sections=[{'heading':'Amount direction and refund interpretation','text':'All amounts are signed from the account holder perspective: receipts positive, payments negative. Customer refunds paid out are negative; expense refunds received are positive. Generic refund labels remain uncertain. Net cash flow is not taxable income. Values exceeding Excel numeric precision are preserved as exact decimal text.'},{'heading':'Reporting period','text':f"{reconciliation['period']['start']} through {reconciliation['period']['end']}. Amounts remain separated by currency. Transfers are excluded from income. This is preparation from supplied records, not a tax assessment."},{'heading':'Missing evidence and decisions','text':'\n'.join(reconciliation['questions']) or 'No unresolved item detected in supplied records; complete account coverage still requires confirmation.'},{'heading':'Reconciliation controls','text':f"{len(reconciliation['duplicates'])} stable-identity duplicates removed; {len(reconciliation['matched_transfers'])} transfer pairs matched. Expected account coverage is {'complete' if reconciliation['coverage_complete'] else 'incomplete or not established'}."}]
        mappings=list(dict.fromkeys(f"{r['source']} {r['source_row']}" for r in reconciliation['transactions']))
        sections.append({'heading':'Evidence mapping','text':'\n'.join(mappings[:100]) + ('\nAdditional source rows are listed in the accompanying workbook.' if len(mappings)>100 else '')})
        parent_ids=parent_ids or {}
        if not isinstance(parent_ids,dict) or set(parent_ids)-{'xlsx','csv','docx','pdf'}:raise ValueError('Use explicit parent IDs keyed by output format')
        for fmt,identity in parent_ids.items():
            parent=self.documents.get(identity,conversation_id)
            if parent['source']!='generated-fixed-operation' or not parent['storage_name'].endswith('.'+fmt):raise ValueError('Revision parent format differs')
        outputs=[]
        for fmt in ('xlsx','csv','docx','pdf'):
            tables=[summary,transactions] if fmt=='xlsx' else [transactions] if fmt=='csv' else [summary]
            outputs.append(self.documents.generate(conversation_id=conversation_id,format=fmt,title=title,sections=sections,tables=tables,source_ids=source_ids,parent_id=parent_ids.get(fmt),turn_id=turn_id,review_status=review_status))
        return outputs


@exact_arithmetic
def tax_preparation_pack(reconciliation, *, tax_year, jurisdiction, taxpayer_facts, official_sources, assumptions=(), assets=None):
    """Build a traceable readiness pack, never invent residency, rates or filing duty."""
    if jurisdiction != 'Pakistan' or not isinstance(tax_year,int) or isinstance(tax_year,bool) or not 2000<=tax_year<=2100:
        raise ValueError('Explicit Pakistan test/reporting tax year required')
    from urllib.parse import urlparse
    for source in official_sources:
        url=urlparse(source['url'])
        if url.scheme!='https' or not (url.hostname=='fbr.gov.pk' or (url.hostname or '').endswith('.fbr.gov.pk')):
            raise ValueError('Tax authority source must be HTTPS FBR')
        if not all(source.get(k) for k in ('title','retrieved_at','applicable_period','excerpt','sha256')):
            raise ValueError('Retain source version, period, retrieval date and exact supporting excerpt')
        stamp=datetime.fromisoformat(source['retrieved_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError('Source retrieval timestamp needs timezone')
        if hashlib.sha256(source['excerpt'].encode()).hexdigest()!=source['sha256']:
            raise ValueError('Source excerpt hash mismatch')
    questions=list(reconciliation['questions'])
    for key in ('residency','tax_year_basis','income_types','filing_status','asset_liability_coverage'):
        if not taxpayer_facts.get(key): questions.append(f'Owner fact needed: {key.replace("_"," ")}')
    basis=taxpayer_facts.get('tax_year_basis')
    if isinstance(basis,dict) and basis.get('start') and basis.get('end') and reconciliation.get('period')!={'start':basis['start'],'end':basis['end']}:questions.append('Financial report period differs from the explicitly selected tax-year period; full-period records are required')
    if not reconciliation.get('coverage_complete'):questions.append('Financial record/account coverage is incomplete or not established; no final tax conclusions')
    if reconciliation.get('totals_provisional'):questions.append('Resolve or expressly review provisional financial classifications before tax mapping')
    if not official_sources: questions.append('Current applicable-period FBR source verification required')
    if any(str(tax_year) not in s['applicable_period'] for s in official_sources): questions.append('General guidance is not proof of applicable-year rates or forms; verify period-specific rules')
    wealth=None
    if assets:
        opening=amount(assets['opening_net_assets']); closing=amount(assets['closing_net_assets'])
        explained=amount(assets['income'])-amount(assets['expenses'])+amount(assets.get('other_explained_change','0'))
        wealth={'currency':assets['currency'],'net_asset_change':str(closing-opening),'explained_change':str(explained),'unexplained_difference':str(closing-opening-explained),'source':assets.get('source'),'status':'arithmetic reconciliation only; legal classification requires review'}
        if not assets.get('source'):questions.append('Wealth balances and explanation need source evidence')
        if closing-opening!=explained: questions.append('Wealth reconciliation difference needs supporting evidence')
    return {'title':f'Pakistan tax year {tax_year} filing preparation','jurisdiction':jurisdiction,'tax_year':tax_year,'facts':taxpayer_facts,'record_summary':reconciliation,'sources':official_sources,'assumptions':list(assumptions),'wealth_reconciliation':wealth,'unresolved_decisions':questions,'portal_entry_plan':['Confirm taxpayer identity, reporting period and residency with owner.','Check applicable official return and wealth-statement forms.','Map each evidenced income, expense, asset and liability to the verified form fields.','Reconcile figures and retain source references and unresolved decisions.','Review draft entries with owner or qualified adviser.','Stop before final declaration, submission or payment; fresh owner decision required.'],'independent_review':{'status':'required','interpretations_verified':False},'submission_authorized':False}
