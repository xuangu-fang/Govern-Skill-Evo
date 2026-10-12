"""Interface 0.2: typed predictions and explicit public operation identity semantics.

No business rules, fixtures, actions or evaluator changes. Frozen 0.1 remains intact.
"""
from benchmark_v5.core import tool,ToolError
from .environment import Settlement,Evidence

OPERATION_POLICY=('操作号operation_id由Agent为每一个新的业务写操作自行选择新的非空字符串。'
    '它不是必须向服务端查询的既有凭证。只有重试同一接口同一载荷时才复用原号；'
    '不同接口或载荷必须用新号。receipt_id则必须使用真实返回的收件/补件凭证。')


class SettlementV02(Settlement):
    def request(self):
        r=super().request();r['policy']+=' '+OPERATION_POLICY
        r['diagnostic']='在首次业务写入前，可对每个允许退货商品分别调用predict_return给出金额/释放预测。无法判断的商品可跳过；预测不影响S。'
        return r

    def record_prediction(self,predictions):
        # Shadow inherited decorator, so the ambiguous multi-mechanism tool is not exposed.
        raise ToolError('USE_TYPED_PREDICTION_TOOL')

    @tool
    def predict_return(self,item_id: str,refund_cents: int,available_on_acceptance: bool):
        """Record one item's predicted refund and release before any business write. No grading feedback.

        Call once per allowed return item. You may omit items whose outcome is uncertain.
        """
        if self.state['operations']:raise ToolError('PREDICTION_WINDOW_CLOSED')
        if item_id not in self.scenario['allowed_returns']:raise ToolError('UNKNOWN_RETURN_OPTION')
        if refund_cents<0:raise ToolError('NONNEGATIVE_CENTS_REQUIRED')
        if self.state['prediction'] is None:self.state['prediction']={}
        if item_id in self.state['prediction']:raise ToolError('PREDICTION_ALREADY_RECORDED')
        self.state['prediction'][item_id]=dict(refund_cents=refund_cents,available_on_acceptance=available_on_acceptance)
        return {'recorded':True,'item_id':item_id}


class EvidenceV02(Evidence):
    def request(self):
        r=super().request();r['public_policy']+=' '+OPERATION_POLICY
        r['diagnostic']='首次业务写入前，可调用predict_documents预测所有当前合法可得资料是否充分。无法判断可跳过；预测不影响S/C。'
        return r

    def record_prediction(self,predictions):
        raise ToolError('USE_TYPED_PREDICTION_TOOL')

    @tool
    def predict_documents(self,available_documents_sufficient: bool):
        """Record whether all currently lawful available documents suffice before any business write.

        This is a diagnostic declaration, not a business precheck; no answer is returned.
        """
        if self.state['operations'] or self.state['prediction'] is not None:raise ToolError('PREDICTION_WINDOW_CLOSED')
        self.state['prediction']={'available_documents_sufficient':available_documents_sufficient}
        return {'recorded':True}


def build(case,world):
    return (SettlementV02 if case['kind']=='LS1' else EvidenceV02)(case,world)
