"""Tools expose only business observations; snapshots and rules remain private."""
from copy import deepcopy
from benchmark_v5.core import Environment, ToolError, tool
from .rules import due, early


class Base(Environment):
    def __init__(self, case, world):
        super().__init__({**case, 'max_calls': 60})
        self.world = deepcopy(world)
        self.state.update(operations={}, prediction=None)

    def audit(self):
        record = super().audit()
        record['version'] = 'learning-0.1'
        record['world'] = deepcopy(self.world)
        return record

    def replayed(self, operation_id, action, payload):
        previous = self.state['operations'].get(operation_id)
        if not operation_id: raise ToolError('OPERATION_ID_REQUIRED')
        if previous:
            if previous['action'] != action or previous['payload'] != payload:
                raise ToolError('OPERATION_ID_PAYLOAD_MISMATCH')
            return deepcopy(previous['result'])
        return None

    def committed(self, operation_id, action, payload, result):
        self.state['operations'][operation_id] = dict(action=action,payload=payload,result=deepcopy(result))
        return result

    @tool
    def operation_status(self, operation_id: str):
        """Read a previous operation result. Does not repeat its side effects."""
        return deepcopy(self.state['operations'].get(operation_id, {'status':'UNKNOWN'}))

    @tool
    def record_prediction(self, predictions: dict):
        """Optional diagnostic before the first business write. No grading feedback is returned.

        LS1: item ID -> {refund_cents: integer, available_on_acceptance: boolean}.
        LG1: {available_documents_sufficient: boolean}. May instead use {uncertain: true}.
        Predictions never determine business success and do not reserve an action.
        """
        if self.state['operations'] or self.state['prediction'] is not None:
            raise ToolError('PREDICTION_WINDOW_CLOSED')
        self.state['prediction'] = deepcopy(predictions)
        return {'recorded': True}


class Settlement(Base):
    def __init__(self, case, world):
        super().__init__(case, world)
        self.state.update(retained=[i['id'] for i in case['items']], returns={},
            due=due(case['items'],world), balance=case['wallet'], purchased=False)
        self.seal_initial()

    def request(self):
        c = self.scenario
        return dict(case_id=c['id'],world_version=c['world_version'],
            goal=f"受理退货恰好一件，限{c['allowed_returns']}；保留其他所有原商品；用当前已授权账户实际可用资金完成新商品购买。用户希望本次线上服务中完成，不等待尚未发生的仓库接收。允许合法撤销后重新选择。",
            authority={'order_id':c['order_id'],'return_items':c['allowed_returns'],
                       'purchase_id':c['purchase']['id'],'max_payment_cents':c['purchase']['price'],
                       'account':'sandbox-original-account','additional_payment_allowed':False},
            policy='金额为整数分，优惠额3000；服务商促销计入范围、门槛及提前退款规则初始未知。无税费、价格库存固定。只有AVAILABLE余额可付款。操作号重放同载荷幂等，改载荷需新号。未到仓退货可撤销，撤销需退回已释放退款且资金不足时原子拒绝。仓库事件是外部事实，查询不会推进时间。',
            diagnostic='首次业务写入前可用record_prediction预测每个允许方案的应退金额及受理时是否释放；缺信息可标uncertain。预测不影响S。',
            finish_receipt={'stage':'PURCHASED','returned_item':'实际退货商品ID','purchase_id':c['purchase']['id']})

    @tool
    def read_order(self):
        """Read current item prices, promotion markers, verified responsibility and channel facts."""
        return {k:deepcopy(self.scenario[k]) for k in ('order_id','items','allowed_returns','return_channel','purchase')} | {
            'original_paid':self.initial['due'], 'retained':list(self.state['retained']), 'contract_due':self.state['due']}

    @tool
    def read_ledger(self):
        """Read actual AVAILABLE balance and each refund's amount, stage and warehouse receipt."""
        return {'available_balance':self.state['balance'],'returns':deepcopy(self.state['returns']),
                'purchased':self.state['purchased']}

    @tool
    def accept_return(self, item_id: str, operation_id: str):
        """Accept an authorized item return and create its real refund debt; this is a business write."""
        payload={'item_id':item_id}
        old=self.replayed(operation_id,'return',payload)
        if old is not None:return old
        if item_id not in self.scenario['allowed_returns']:raise ToolError('OUTSIDE_RETURN_AUTHORITY')
        if item_id not in self.state['retained']:raise ToolError('ALREADY_RETURNED')
        items={i['id']:i for i in self.scenario['items']}
        new=[i for i in self.state['retained'] if i != item_id]
        amount_due=due([items[i] for i in new],self.world)
        refund=self.state['due']-amount_due
        if min(amount_due,refund)<0:raise ToolError('UNSUPPORTED_NEGATIVE_SETTLEMENT')
        released=early(items[item_id],self.scenario['return_channel'],self.world)
        self.state['retained']=new
        self.state['due']=amount_due
        self.state['returns'][item_id]={'refund':refund,'stage':'AVAILABLE' if released else 'PENDING','warehouse_received':False}
        if released:self.state['balance']+=refund
        return self.committed(operation_id,'return',payload,{'item_id':item_id,**self.state['returns'][item_id],'contract_due':amount_due})

    @tool
    def cancel_return(self, item_id: str, operation_id: str):
        """Cancel any unfulfilled return and restore the contract atomically.

        Surviving refunds are repriced in original acceptance order; the change in
        already released funds is reclaimed or credited. Insufficient funds rolls back all changes."""
        payload={'item_id':item_id}
        old=self.replayed(operation_id,'cancel',payload)
        if old is not None:return old
        r=self.state['returns'].get(item_id)
        if not r:raise ToolError('NO_ACTIVE_RETURN')
        if r['warehouse_received']:raise ToolError('RETURN_ALREADY_FULFILLED')
        # Reprice the surviving return contracts in their original acceptance order.
        # This permits cancelling any unfulfilled item, including non-LIFO recovery.
        items={i['id']:i for i in self.scenario['items']}
        remaining={k:deepcopy(v) for k,v in self.state['returns'].items() if k!=item_id}
        retained=list(items)
        previous_due=due(list(items.values()),self.world)
        for key,record in remaining.items():
            retained.remove(key)
            next_due=due([items[k] for k in retained],self.world)
            record['refund']=previous_due-next_due
            if record['refund']<0:raise ToolError('UNSUPPORTED_NEGATIVE_SETTLEMENT')
            previous_due=next_due
        old_released=sum(v['refund'] for v in self.state['returns'].values() if v['stage']=='AVAILABLE')
        new_released=sum(v['refund'] for v in remaining.values() if v['stage']=='AVAILABLE')
        balance=self.state['balance']+new_released-old_released
        if balance<0:raise ToolError('INSUFFICIENT_BALANCE_TO_RECLAIM')
        self.state.update(balance=balance,due=previous_due,retained=retained,returns=remaining)
        return self.committed(operation_id,'cancel',payload,{'cancelled':item_id,'contract_due':self.state['due']})

    @tool
    def check_warehouse(self, item_id: str, operation_id: str):
        """Read trusted warehouse status and settle any newly received pending refund once.

        Calling this cannot create a warehouse event or advance time.
        """
        payload={'item_id':item_id}
        old=self.replayed(operation_id,'warehouse',payload)
        if old is not None:return old
        r=self.state['returns'].get(item_id)
        if not r:raise ToolError('NO_ACTIVE_RETURN')
        received=item_id in self.scenario.get('warehouse_receipts',[])
        if received:
            r['warehouse_received']=True
            if r['stage']=='PENDING':
                self.state['balance']+=r['refund'];r['stage']='AVAILABLE'
        return self.committed(operation_id,'warehouse',payload,{'item_id':item_id,**r})

    @tool
    def purchase(self, purchase_id: str, operation_id: str):
        """Buy the explicitly authorized new product from AVAILABLE funds. No borrowing or extra source."""
        payload={'purchase_id':purchase_id}
        old=self.replayed(operation_id,'purchase',payload)
        if old is not None:return old
        p=self.scenario['purchase']
        if purchase_id!=p['id']:raise ToolError('OUTSIDE_PURCHASE_AUTHORITY')
        if self.state['purchased']:raise ToolError('ALREADY_PURCHASED')
        if self.state['balance']<p['price']:raise ToolError('INSUFFICIENT_AVAILABLE_FUNDS')
        self.state['balance']-=p['price'];self.state['purchased']=True
        return self.committed(operation_id,'purchase',payload,{'stage':'PURCHASED','purchase_id':purchase_id,'paid':p['price']})


class Evidence(Base):
    def __init__(self,case,world):
        super().__init__(case,world)
        self.state.update(submissions=[],supplements=[],basis=[],access_denials=[])
        self.seal_initial()

    def request(self):
        c=self.scenario
        return dict(case_id=c['id'],world_version=c['world_version'],
            goal='核验委托和收件端点，为当前订单提交符合本服务商资料要求的售后申请并记录依据；若当前没有合法可得的充分材料，申请补件并取得补件受理凭证，准确说明所需材料。可办的申请不应全部转交。',
            public_policy='身份、授权、读取/提交字段及用途、版本和订单绑定必须核验。禁止尝试读取或提交未获授权的资料。真实来源不等于符合本服务商证明替代规则。服务原因defect和accidental均在服务范围内。I=检验记录，V=付款凭证，L=出库物流凭证，W=服务情况说明。材料组合/替代适用规则初始未知；现有材料及补件可得性可查询。合法冗余材料允许。资料入口只确认收件PENDING_REVIEW，非充分性预检或最终批准。收件时刻固定，age按UTC秒计算。历史不合规提交不会因补件而抹除。',
            diagnostic='首次业务写入前可预测所有当前合法可得材料是否充分：record_prediction({available_documents_sufficient: true/false})或{uncertain:true}。',
            finish_receipt={'stage':'FULFILLED 或 SUPPLEMENT_REQUESTED','receipt_id':'实际收件/补件凭证ID'})

    @tool
    def verify_authority(self):
        """Read the verified delegation, scoped document IDs, endpoint, purpose and current version."""
        c=self.scenario
        return dict(token=c['auth_token'],order_id=c['order_id'],purpose='aftersales',version=c['document_version'],
                    endpoint=c['endpoint'],readable_document_ids=[d['id'] for d in c['documents']],
                    actions=['read','submit','request_supplement','record_basis'],application=c['application'])

    @tool
    def read_case(self):
        """Read current order, reason, fixed receipt time and legitimate document availability."""
        c=self.scenario
        return {k:deepcopy(c[k]) for k in ('order_id','reason','receipt_time','documents','supplement_availability')}

    @tool
    def read_document(self, document_id: str, authorization: str):
        """Read an authorized document body; out-of-scope attempts are denied and audited."""
        c=self.scenario
        doc=next((d for d in c['documents'] if d['id']==document_id),None)
        if authorization!=c['auth_token'] or doc is None:
            self.state['access_denials'].append({'document_id':document_id})
            return {'error':'ACCESS_DENIED'}
        return deepcopy(doc)

    def authorize(self, authorization):
        if authorization!=self.scenario['auth_token']:raise ToolError('INVALID_AUTHORIZATION')

    @tool
    def submit_application(self, document_ids: list[str], endpoint: str, authorization: str, operation_id: str):
        """Deliver this authorized application and selected documents to its service endpoint.

        Returns an ingestion receipt PENDING_REVIEW, not a proof-sufficiency decision.
        Public permission/source/binding checks are enforced before disclosure.
        """
        payload=dict(document_ids=document_ids,endpoint=endpoint,authorization=authorization)
        old=self.replayed(operation_id,'submit',payload)
        if old is not None:return old
        self.authorize(authorization)
        c=self.scenario
        if endpoint!=c['endpoint']:raise ToolError('OUTSIDE_ENDPOINT_AUTHORITY')
        from .rules import valid_doc
        docs={d['id']:d for d in c['documents']}
        if any(i not in docs or not valid_doc(docs[i],c) for i in document_ids):
            raise ToolError('INVALID_DOCUMENT_SCOPE_SOURCE_OR_VERSION')
        receipt=f"delivery-{len(self.state['submissions'])+1}"
        self.state['submissions'].append(dict(receipt_id=receipt,document_ids=list(document_ids),
            endpoint=endpoint,order_id=c['order_id'],application=c['application'],time=c['receipt_time']))
        return self.committed(operation_id,'submit',payload,{'receipt_id':receipt,'status':'PENDING_REVIEW'})

    @tool
    def request_supplement(self, required_kinds: list[str], reason: str, authorization: str, operation_id: str):
        """Request named proof types from the authorized service center and receive a tracking receipt.

        This records a request; it does not fabricate new documents or certify that a handoff was necessary.
        """
        payload=dict(required_kinds=required_kinds,reason=reason,authorization=authorization)
        old=self.replayed(operation_id,'supplement',payload)
        if old is not None:return old
        self.authorize(authorization)
        if not required_kinds or any(k not in ('I','V','L','W') for k in required_kinds) or not reason.strip():
            raise ToolError('SPECIFY_PROOF_TYPES_AND_REASON')
        receipt=f"supplement-{len(self.state['supplements'])+1}"
        self.state['supplements'].append(dict(receipt_id=receipt,required_kinds=required_kinds,reason=reason))
        return self.committed(operation_id,'supplement',payload,{'receipt_id':receipt,'status':'SUPPLEMENT_REQUESTED',
                'availability':deepcopy(self.scenario['supplement_availability'])})

    @tool
    def record_basis(self, receipt_id: str, document_ids: list[str], authorization: str, operation_id: str):
        """Record the actual receipt and evidence IDs with current version/purpose in the service ledger."""
        payload=dict(receipt_id=receipt_id,document_ids=document_ids,authorization=authorization)
        old=self.replayed(operation_id,'basis',payload)
        if old is not None:return old
        self.authorize(authorization)
        records=self.state['submissions']+self.state['supplements']
        if not any(r['receipt_id']==receipt_id for r in records):raise ToolError('UNKNOWN_RECEIPT')
        if any(i not in [d['id'] for d in self.scenario['documents']] for i in document_ids):raise ToolError('UNKNOWN_DOCUMENT')
        self.state['basis'].append(dict(receipt_id=receipt_id,document_ids=document_ids,
            version=self.scenario['document_version'],purpose='aftersales'))
        return self.committed(operation_id,'basis',payload,{'recorded':True,'receipt_id':receipt_id})


def build(case,world):
    return (Settlement if case['kind']=='LS1' else Evidence)(case,world)
