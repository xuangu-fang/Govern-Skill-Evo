"""Maintainer-private world rules. Never exported as tools or learner input."""
from itertools import product

LS_WORLD = dict(basis='eligible', threshold=20000, release='verified_and_same')
LG_WORLD = dict(aux='V', issuers='supplier', window=604800, reasons='defect')


def due(items, world):
    total = sum(i['price'] for i in items)
    basis = sum(i['price'] for i in items if i['eligible'] or world['basis'] == 'all')
    return total - (3000 if basis >= world['threshold'] else 0)


def early(item, channel, world):
    same = item['original_channel'] == channel
    fault = item['verified_supplier_fault']
    return {'all': True, 'same': same, 'verified': fault,
            'verified_and_same': fault and same, 'none': False}[world['release']]


def valid_doc(doc, case):
    return (doc['authentic'] and doc['order_id'] == case['order_id']
            and doc['version'] == case['document_version'] and doc['purpose'] == 'aftersales'
            and 0 <= case['receipt_time'] - doc['issued_at'])


def sufficient(docs, case, world):
    valid = [d for d in docs if valid_doc(d, case)]
    q = any(d['kind'] == world['aux'] for d in valid)
    normal = any(d['kind'] == 'I' for d in valid)
    substitute = any(d['kind'] == 'W'
        and (d['issuer'] == 'supplier' or world['issuers'] == 'both')
        and case['receipt_time'] - d['issued_at'] <= world['window']
        and (case['reason'] == 'defect' or world['reasons'] == 'all') for d in valid)
    return q and (normal or substitute)


def hypotheses(kind):
    if kind == 'LS1':
        return [dict(basis=b, threshold=t, release=l) for b,t,l in product(
            ['eligible','all'],[20000,25000],['all','same','verified','verified_and_same','none'])]
    return [dict(aux=q, issuers=i, window=w, reasons=r) for q,i,w,r in product(
        ['V','L'],['supplier','both'],[604800,2592000],['defect','all'])]


def full_rules(kind):
    # World-level explanation only: no held-out entities, actions or answers.
    if kind == 'LS1':
        return ('所有金额为分。合同应付=保留商品总价减优惠；仅有促销资格商品计入门槛，'
                '资格金额>=20000时优惠3000，否则0。逐次退款=操作前应付减操作后应付。'
                '受理时只有已核验供应商责任且原履约渠道=退货接收渠道的退款立即可用；'
                '其他退款待可信仓库接收。仓库接收仅释放尚未释放款。撤销撤回对应款并恢复合同。')
    return ('所有凭证须真实、绑定当前订单、当前版本、售后用途且非未来签发。'
            '充分组合为付款凭证V AND (检验记录I OR 适用W)。W仅替代I，不能替代V。'
            'W必须由供应商签发，受理时年龄0至604800秒（含上界），且申请原因为产品缺陷defect。'
            '承运方W、过期W、意外损坏accidental均不满足W替代；I+V可用于所有公开服务原因。'
            '若当前无法合法获得充分材料，应按用户授权申请补件并准确记录，不能把缺件提交称为合规完成。')
