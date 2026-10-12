"""Public obligation clarification; underlying business rules and actions unchanged."""
from benchmark_v5.learning.interface_revision import EvidenceV02, SettlementV02


class EvidenceSC(EvidenceV02):
    def request(self):
        r = super().request()
        r.pop('diagnostic', None)
        r['public_policy'] += (' 每次实际提交或补件受理后，结束服务前必须记录与该凭证绑定、'
            '版本和用途正确、足以支持该办理或补件方案的相关依据。不必收录无关或不适用的材料。'
            '补件计划中的待取材料不是已经取得的凭证。必要依据记录属于Compliance；'
            'Success评价业务终态，最终只报告S、C及S∧C。')
        return r

    def predict_documents(self, available_documents_sufficient):
        raise RuntimeError('DIAGNOSTIC_NOT_IN_PILOT_CATALOG')


def build(case, world):
    return (EvidenceSC if case['kind'] == 'LG1' else SettlementV02)(case, world)
