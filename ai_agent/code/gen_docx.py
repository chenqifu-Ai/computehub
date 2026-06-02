#!/usr/bin/env python3
"""
手动构建 .docx Word 文档（不依赖 lxml / python-docx）
用法：python3 docx_gen.py
输出：全过程咨询服务合作框架协议.docx
"""

import zipfile
import os
import io
import shutil

OUTPUT = "/root/.openclaw/workspace/ai_agent/code/全过程咨询服务合作框架协议.docx"
SRC_MD = "/root/.openclaw/workspace/ai_agent/code/全过程咨询服务合作框架协议.md"

# ---------- 合同内容（纯文本 + 简单标记） ----------
PARAGRAPHS = []

def p(text, bold=False, size=11, alignment=None, space_before=0, space_after=0, space_lines=None, underline=False, italic=False):
    """创建一个段落描述"""
    PARAGRAPHS.append({
        "text": text,
        "bold": bold,
        "size": size,
        "alignment": alignment,
        "space_before": space_before,
        "space_after": space_after,
        "space_lines": space_lines,
        "underline": underline,
        "italic": italic,
    })

def add_newline(count=1):
    for _ in range(count):
        PARAGRAPHS.append({"text": "", "bold": False, "size": 11, "space_before": 0, "space_after": 6, "alignment": None})

# ---- 标题 ----
add_newline(2)
p("全过程咨询服务合作框架协议", bold=True, size=22, alignment="center", space_after=6)
p("— — — — — — — — — —", bold=False, size=12, alignment="center", space_after=18)
add_newline()

# ---- 合同编号 ----
p("合同编号：__________", bold=False, size=11, space_before=6, space_after=18)

# ---- 签约方 ----
def party(label, name, field, value):
    p(f"{label}：{value}" if value else f"{label}：{name}", bold=False, size=11, space_after=3)
    if name:
        p(f"统一社会信用代码：____________________________", bold=False, size=10, space_after=1)
        p(f"法定代表人：__________________________________", bold=False, size=10, space_after=1)
        p(f"地  址：______________________________________", bold=False, size=10, space_after=1)
        p(f"联系人及电话：________________________________", bold=False, size=10, space_after=8)

p("甲方（咨询服务方）：", bold=True, size=12, space_before=12, space_after=2)
party("单位名称", "", "", "")

p("乙方（中标联合体牵头方）：中财海绵城市基金管理（深圳）有限公司", bold=True, size=12, space_before=6, space_after=2)
party("", "中财海绵城市基金管理（深圳）有限公司", "", "")

p("丙方（保证金收存监管方）：", bold=True, size=12, space_before=6, space_after=2)
party("", "", "", "")

add_newline()

# ---- 鉴于条款 ----
p("鉴于条款", bold=True, size=14, alignment="center", space_before=12, space_after=12)

PREAMBLE = [
    ("一、", '招标人"宁德市霞浦生态环境局"已就"**霞浦县美丽海湾建设与产业一体化开发(EOD)项目**"（招标编号：**FJTP-00092418014006**）向乙方发出《中标通知书》。乙方作为联合体牵头方（联合体成员包括：福建建工集团有限责任公司、福建省合道建筑设计有限公司、宁德市东侨经济开发区闽益农农业科技有限公司），确认为该项目中标人。'),
    ("二、", '根据中标通知书要求，乙方须在项目所在地（福建省宁德市霞浦县）与县城投公司合资成立项目公司，由项目公司负责本项目的整体立项、投资、融资、建设、运维及招商工作。中标通知书规定的时间线为：收到中标通知后30个日历日内签订《投资合作协议》，签订合作协议后30个日历日内签订《股东协议》并设立项目公司，项目公司设立后30个日历日内签订《EOD项目合同》。'),
    ("三、", '本项目暂定估算投资约 **贰拾玖亿肆仟柒佰壹拾肆万陆仟伍佰元整（¥2,947,146,500.00）**，其中生态环境治理类项目约 **玖亿肆仟伍佰伍拾叁万伍仟肆佰元整（¥945,535,400.00）**（占比约32%），生态产业开发类项目约 **贰拾亿零壹佰陆拾壹万壹仟肆佰元整（¥2,001,611,100.00）**（占比约68%）。整体合作期为 **贰拾贰年**（建设期不超过叁年+运营期壹拾玖年）。'),
    ("四、", "甲方具备全过程工程咨询服务能力和相应资质，乙方认可甲方的专业能力和项目经验，双方一致同意就甲方为上述项目公司（筹）提供全过程咨询服务事宜建立战略合作关系。"),
    ("五、", "为保障甲方履约诚意，甲方自愿向丙方支付履约保证金人民币 **贰佰万元整（¥2,000,000.00）**，丙方作为独立的第三方对保证金进行收存与监管，按照本协议约定的条件和程序予以退还或处置。"),
]

for num, content in PREAMBLE:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

add_newline()
p("为此，甲、乙、丙三方经平等协商，依据《中华人民共和国民法典》及相关法律法规，达成如下协议，以兹共同遵守：", bold=False, size=11, space_before=6, space_after=18)

# ---- 第一条 定义与解释 ----
p("第一条 定义与解释", bold=True, size=14, alignment="center", space_before=18, space_after=12)

ARTICLE1 = [
    ('1.1', '"本项目" 指"霞浦县美丽海湾建设与产业一体化开发(EOD)项目"（招标编号：FJTP-00092418014006），包括其包含的全部4个子项目：\n\n  （1）霞浦县城区入海河流水生态环境综合治理提升项目；\n  （2）霞浦县东冲半岛东部岸段美丽海湾生态环境综合整治与生态保护修复项目；\n  （3）霞浦县松山生态文旅综合提升及配套基础设施建设（一期）工程项目；\n  （4）霞浦县东冲半岛多元融合经济产业综合开发项目。'),
    ('1.2', '"项目公司" 指乙方在霞浦县与县城投公司合资设立、负责本项目整体立项、投资、融资、建设、运维及招商工作的有限责任公司。'),
    ('1.3', '"目标咨询服务" 指甲方拟为项目公司提供的全过程工程咨询服务，包括但不限于：项目前期策划咨询、投融资结构设计与融资顾问、建设期全过程管理咨询、运营期管理咨询、产业招商及资源对接服务、以及项目相关的专项咨询服务。'),
    ('1.4', '"目标咨询合同" 指甲方与项目公司（筹）就目标咨询服务签订的具体服务合同。'),
    ('1.5', '"履约保证金" 指甲方根据本协议约定向丙方支付的人民币 **贰佰万元整（¥2,000,000.00）** 保证金。'),
    ('1.6', '"县城投公司" 指霞浦县城市建设投资发展集团有限公司或其在项目所在地设立的投资主体。'),
]

for num, content in ARTICLE1:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

# ---- 第二条 合作内容与乙方承诺 ----
p("第二条 合作内容与乙方承诺", bold=True, size=14, alignment="center", space_before=18, space_after=12)

p("2.1 合作目标", bold=True, size=11, space_before=6, space_after=4)
p("乙方承诺在项目公司依法设立后，积极推荐甲方作为目标咨询服务的首选供应商，并全力协调推动项目公司与甲方签订目标咨询合同。", bold=False, size=11, space_after=8)

p("2.2 乙方具体承诺", bold=True, size=11, space_before=6, space_after=4)
PROMISES = [
    "项目公司设立后 **三十（30）个日历日内**，乙方向项目公司出具书面推荐函，正式推荐甲方为本项目全过程咨询服务供应商；",
    "乙方承诺在目标咨询服务采购、比选、谈判过程中，协调项目公司与甲方进行实质性磋商，确保甲方获得公平、合理的签约机会；",
    "乙方不得故意设置不合理条件或提出排他性条款，阻挠甲方与项目公司签订目标咨询合同；",
    "乙方确认已审阅甲方的专业能力资料，认可甲方具备承接本项目目标咨询服务的能力与资质；",
    "乙方应积极配合甲方参与项目公司筹备工作，包括但不限于参加相关会议、提供项目必要的技术资料和背景信息。",
]
for i, prom in enumerate(PROMISES, 1):
    p(f"（{i}）{prom}", bold=False, size=11, space_after=6)

p("2.3 本协议项下的乙方承诺不构成乙方对目标咨询合同具体条款的保证或承诺。目标咨询合同的具体服务范围、费用、期限等，由甲方与项目公司另行协商确定。", bold=False, size=11, space_before=8, space_after=8)

# ---- 第三条 甲方的权利与义务 ----
p("第三条 甲方的权利与义务", bold=True, size=14, alignment="center", space_before=18, space_after=12)

p("3.1 履约保证金支付", bold=True, size=11, space_before=6, space_after=4)
p('甲方应于本协议签署之日起 **七（7）个工作日内**，将履约保证金人民币 **贰佰万元整（¥2,000,000.00）** 一次性足额支付至丙方指定账户：', bold=False, size=11, space_after=4)
p("  开户名：________________________", bold=False, size=11, space_after=2)
p("  开户行：________________________", bold=False, size=11, space_after=2)
p("  账  号：________________________", bold=False, size=11, space_after=8)

p("3.2 能力证明材料", bold=True, size=11, space_before=6, space_after=4)
p("甲方应于本协议签署之日起 **五（5）个工作日内**，向乙方提供以下资料：", bold=False, size=11, space_after=4)
DOCS = ["企业营业执照副本复印件（加盖公章）", "相关行业资质证书复印件", "近三年内类似项目业绩证明材料", "核心服务团队简介及资质证书", "其他乙方合理要求的能力证明文件"]
for i, doc in enumerate(DOCS, 1):
    p(f"  （{i}）{doc}", bold=False, size=11, space_after=2)

p("3.3 甲方应积极、诚信地履行本协议项下各项义务，积极配合项目筹备工作，不得无故拖延或拒绝参与项目相关谈判。", bold=False, size=11, space_before=8, space_after=6)
p("3.4 甲方保证其为履行本协议及将来可能签订的目标咨询合同而提供的所有资质证明文件均真实、合法、有效。如有虚假，甲方承担全部责任。", bold=False, size=11, space_after=8)

# ---- 第四条 履约保证金的收存与监管 ----
p("第四条 履约保证金的收存与监管", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES4 = [
    ("4.1 收存确认", "丙方收到甲方支付的履约保证金后，应于 **两个工作日内** 向甲方出具收款确认凭证，并确认保证金进入专项监管账户。"),
    ("4.2 监管方式", "丙方保证履约保证金存放于独立监管账户，在保证金未被依约退还或处置前，丙方不得擅自挪用、质押或作任何处分。"),
    ("4.3 账户变更", "如需变更收款账户，丙方须提前 **十（10）个工作日** 书面通知甲方和乙方。"),
    ("4.4 利息归属", "履约保证金在监管期间产生的利息归甲方所有。"),
]
for title, content in CLAUSES4:
    p(f"{title}：{content}", bold=False, size=11, space_after=8)

# ---- 第五条 履约保证金的退还与处置 ----
p("第五条 履约保证金的退还与处置", bold=True, size=14, alignment="center", space_before=18, space_after=12)

p("5.1 无条件全额退还情形", bold=True, size=11, space_before=6, space_after=4)
p("出现以下 **任一** 情形时，甲方有权书面要求丙方在 **五（5）个工作日内** 将履约保证金全额无息退还至甲方原支付账户：", bold=False, space_after=4)
REFUND = [
    "本协议签署之日起满 **九（9）个月**，项目公司尚未依法设立的；",
    "项目公司依法设立之日起满 **六（6）个月**，甲方与项目公司仍未签订目标咨询合同的，且该等情形非因甲方原因导致的；",
    "本项目因政策调整、政府决策调整、招标取消、中标无效或其他不可归责于各方的原因而终止或无法继续推进的；",
    "乙方违反本协议第二条约定的义务，包括但不限于故意设置不合理条件、消极不作为、出具虚假推荐函等，导致甲方无法获得公平签约机会的；",
    "乙方与县城投公司未能就本项目签订《投资合作协议》或《股东协议》的；",
    "经甲、乙、丙三方协商一致同意终止本协议的。",
]
for i, r in enumerate(REFUND, 1):
    p(f"  （{i}）{r}", bold=False, size=11, space_after=4)

p("5.2 保证金转化", bold=True, size=11, space_before=10, space_after=4)
p("甲方与项目公司成功签订目标咨询合同后，甲方有权书面要求丙方在 **五（5）个工作日内** 将履约保证金转入甲方指定账户。甲方与项目公司可自行协商将该笔款项作为目标咨询合同的履约保证金或服务预付款。", bold=False, size=11, space_after=8)

p("5.3 不予退还情形", bold=True, size=11, space_before=10, space_after=4)
p("出现以下任一情形时，乙方有权书面通知丙方不予退还履约保证金，丙方在收到乙方书面通知并核实后 **五（5）个工作日内** 将履约保证金转为乙方的合理损失补偿：", bold=False, size=11, space_after=4)
NON_REFUND = [
    "甲方在乙方出具推荐函后，无正当理由书面声明放弃与项目公司签订目标咨询合同的；",
    "因甲方资质虚假、能力不足等甲方自身原因，导致项目公司拒绝与甲方签订目标咨询合同的；",
    "甲方违反本协议第三条约定，严重拖延或拒绝配合项目相关工作的。",
]
for i, n in enumerate(NON_REFUND, 1):
    p(f"  （{i}）{n}", bold=False, size=11, space_after=4)

p("5.4 退还操作流程", bold=True, size=11, space_before=10, space_after=4)
PROC = [
    "甲方或乙方依据第5.1条或第5.3条要求退还或不予退还履约保证金的，应向丙方提交书面通知及证明材料；",
    "丙方在收到书面通知后 **三（3）个工作日内** 进行形式审核；",
    "如甲乙双方对该次退还/不予退还是否符合本协议约定存在争议，丙方有权暂停执行并书面通知甲乙双方，待甲乙双方协商一致或有权机关作出终局裁决后执行；",
    "如争议期间届满超过 **三十（30）日** 仍无法达成一致的，任何一方均可向本协议约定的管辖法院提起诉讼。",
]
for i, pr in enumerate(PROC, 1):
    p(f"  （{i}）{pr}", bold=False, size=11, space_after=4)

# ---- 第六条 协议期限与终止 ----
p("第六条 协议期限与终止", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES6 = [
    ("6.1", "本协议自各方法定代表人或授权代表签字并加盖公章之日起生效。"),
    ("6.2", "本协议有效期及履行期限至以下情形发生之日止（以较早者为准）：（1）甲方与项目公司签订目标咨询合同，且履约保证金已按本协议第5.2条转化处置完毕；（2）履约保证金已按本协议第5.1条全额退还甲方；（3）履约保证金已按本协议第5.3条不予退还完毕；（4）本协议依照其他约定解除或终止。"),
    ("6.3", "本协议解除或终止后，第五条约定的保证金退还与处置条款仍继续有效，直至保证金全部退还或处置完毕。"),
]
for num, content in CLAUSES6:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

# ---- 第七条 保密条款 ----
p("第七条 保密条款", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES7 = [
    ("7.1", "各方对本协议的内容、本协议签署过程中获知的其他方商业秘密以及因履行本协议而知悉的项目相关信息均负有保密义务。"),
    ("7.2", "未经其他方事先书面同意，任何一方不得向第三方披露本协议内容或前述商业秘密，但法律法规要求披露或向各方的法律顾问、财务顾问等专业人士披露的除外。"),
    ("7.3", "保密义务自本协议生效之日起至本协议终止后 **三（3）年** 内持续有效。"),
]
for num, content in CLAUSES7:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

# ---- 第八条 违约责任 ----
p("第八条 违约责任", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES8 = [
    ("8.1", "任何一方违反本协议项下任何约定，应承担违约责任，赔偿因此给守约方造成的直接经济损失。"),
    ("8.2", "如乙方违反第二条之约定，包括但不限于消极不作为、故意阻挠甲方获得签约机会、向项目公司出具虚假推荐函等，甲方有权要求丙方按第5.1条退还履约保证金，同时甲方有权要求乙方赔偿因此遭受的合理损失（包括但不限于差旅费、咨询方案编制费用等直接支出）。"),
    ("8.3", "丙方违反第四条之约定，擅自挪用、质押保证金造成损失的，丙方应承担全额赔偿责任，并按同期银行贷款利率向甲方支付资金占用期间的利息。"),
]
for num, content in CLAUSES8:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

# ---- 第九条 不可抗力 ----
p("第九条 不可抗力", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES9 = [
    ("9.1", "因地震、台风、洪水、战争、政府行为或其他不能预见、不能避免且不能克服的不可抗力事件，导致本协议不能履行或不能完全履行的，受影响方应在不可抗力事件发生后 **十（10）个工作日内** 书面通知其他各方，并提供相关证明。"),
    ("9.2", "受不可抗力影响的一方，可根据不可抗力的影响程度，部分或全部免除违约责任。但因不可抗力导致无法履行本协议的，各方应协商确定本协议的处理方式（包括但不限于延期履行、解除协议、退还保证金等）。"),
]
for num, content in CLAUSES9:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

# ---- 第十条 争议解决 ----
p("第十条 争议解决", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES10 = [
    ("10.1", "因本协议引起的或与本协议有关的任何争议，各方应首先通过友好协商解决。协商期限为争议发生之日起 **十五（15）日**。"),
    ("10.2", "协商不成的，任何一方均有权向 **甲方所在地** 有管辖权的人民法院提起诉讼。"),
]
for num, content in CLAUSES10:
    p(f"{num} {content}", bold=False, size=11, space_after=8)

# ---- 第十一条 其他条款 ----
p("第十一条 其他条款", bold=True, size=14, alignment="center", space_before=18, space_after=12)

CLAUSES11 = [
    ("11.1 协议独立性", "本协议为框架性合作协议，各方可根据本协议之约定就具体事项另行签署补充协议或具体合同。补充协议与本协议具有同等法律效力，补充协议与本协议不一致的，以补充协议为准。"),
    ("11.2 协议转让", "未经其他各方事先书面同意，任何一方不得将本协议项下的权利和义务转让给第三方。"),
    ("11.3 通知送达", "本协议项下的通知、文件等应以书面形式（包括但不限于电子邮件、传真、挂号信、快递）发送至以下地址。任何一方变更送达地址应提前 **五（5）个工作日** 书面通知其他各方。"),
    ("", "  甲方送达地址：________________________________\n  甲方联系人及电话：______________________________\n\n  乙方送达地址：________________________________\n  乙方联系人及电话：______________________________\n\n  丙方送达地址：________________________________\n  丙方联系人及电话：______________________________"),
    ("11.4 协议份数", "本协议一式 **陆（6）** 份，甲、乙、丙三方各执 **贰（2）** 份，每份具有同等法律效力。"),
    ("11.5 生效条款", "本协议自各方法定代表人或授权代表签字并加盖公章之日起生效。"),
]
for num, content in CLAUSES11:
    if num:
        p(f"{num} {content}", bold=False, size=11, space_after=8)
    else:
        p(content, bold=False, size=11, space_after=18)

add_newline(3)
p("（以下无正文，为签署页）", bold=False, size=11, italic=True, alignment="center", space_after=30)
add_newline(2)

p("签署页", bold=True, size=16, alignment="center", space_before=12, space_after=24)

SIGN = [
    "甲方（盖章）：________________________",
    "法定代表人或授权代表（签字）：__________________",
    "签署日期：______年____月____日",
]
for s in SIGN:
    p(s, bold=False, size=11, space_after=4)

add_newline(3)

SIGN2 = [
    "乙方（盖章）：中财海绵城市基金管理（深圳）有限公司",
    "法定代表人或授权代表（签字）：__________________",
    "签署日期：______年____月____日",
]
for s in SIGN2:
    p(s, bold=False, size=11, space_after=4)

add_newline(3)

SIGN3 = [
    "丙方（盖章）：________________________",
    "法定代表人或授权代表（签字）：__________________",
    "签署日期：______年____月____日",
]
for s in SIGN3:
    p(s, bold=False, size=11, space_after=4)

add_newline(4)
p("附件", bold=True, size=14, alignment="center", space_before=12, space_after=12)

ATTACH = [
    "附件一：甲方资质资料清单\n  （由甲方在本协议签署后五（5）个工作日内提供，包括：1.企业营业执照副本复印件 2.相关行业资质证书复印件 3.近三年类似项目业绩证明 4.核心服务团队简介 5.其他乙方要求的能力证明文件）",
    "",
    "附件二：甲方履约保证金支付凭证\n  （由甲方在支付完成后提供）",
    "",
    "附件三：项目公司设立进度跟踪表\n  （由乙方每季度向甲方书面通报一次）",
]
for a in ATTACH:
    p(a, bold=False, size=11, space_after=10)


# ============================================================
# 构建 .docx（zip 结构）
# ============================================================

def run_properties(rPr_items):
    """构建 <w:rPr> 片段"""
    pr = []
    pr.append('<w:rPr>')
    # 加粗
    if any(i.get('bold') for i in rPr_items):
        pr.append('<w:b w:val="1"/>')
    if any(i.get('italic') for i in rPr_items):
        pr.append('<w:i w:val="1"/>')
    # 字号 (twips)
    sz = max(i.get('size', 11) for i in rPr_items)
    pr.append(f'<w:sz w:val="{sz * 2}"/>')
    # 下划线
    if any(i.get('underline') for i in rPr_items):
        pr.append('<w:u w:val="single"/>')
    # 字体
    pr.append('<w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体" w:cs="宋体"/>')
    # 字号
    pr.append(f'<w:sz w:val="{sz * 2}"/>')
    pr.append('</w:rPr>')
    return ''.join(pr)

def run_text(rPr, text):
    """构建一个 <w:r> 含 <w:t>"""
    return f'<w:r>{rPr}<w:t xml:space="preserve">{text}</w:t></w:r>'

def build_paragraph(rPr_items, text, alignment=None, space_before=0, space_after=0):
    """构建单个 <w:p>"""
    lines = text.split('\n')
    rPr = run_properties(rPr_items)
    runs = [run_text(rPr, line) for line in lines]
    
    al = ''
    if alignment == 'center':
        al = '<w:jc w:val="center"/>'
    elif alignment == 'right':
        al = '<w:jc w:val="right"/>'
    elif alignment == 'justify':
        al = '<w:jc w:val="both"/>'
    
    sb = f' w:spaceBefore="{space_before * 20}"' if space_before else ''
    sa = f' w:spaceAfter="{space_after * 20}"' if space_after else ''
    
    return f'<w:p{sb}{sa}>{al}{"".join(runs)}</w:p>'

# ---------- 构建文档 XML ----------
doc_xml_parts = []

# 文档正文
doc_xml_parts.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
doc_xml_parts.append('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:w16cex="http://schemas.microsoft.com/office/word/2018/wordml/expression" xmlns:w16cid="http://schemas.microsoft.com/office/word/2016/wordml/cid" xmlns:w16="http://schemas.microsoft.com/office/word/2016/wordml" xmlns:w16ex="http://schemas.microsoft.com/office/word/2017/wordml/ex" xmlns:w16ce="http://schemas.microsoft.com/office/word/2018/wordml/cex" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex" mc:Ignorable="w16cx w16cid w16 w16ex w16ce w16se">')

for item in PARAGRAPHS:
    if not item.get('text') and not item.get('bold'):
        # 空行
        doc_xml_parts.append(build_paragraph(
            [{'bold': False, 'size': item.get('size', 11), 'italic': item.get('italic', False)}],
            item.get('text', ''),
            item.get('alignment'),
            item.get('space_before', 0),
            item.get('space_after', 6)
        ))
    elif item.get('text'):
        bold = item.get('bold', False)
        size = item.get('size', 11)
        italic = item.get('italic', False)
        underline = item.get('underline', False)
        doc_xml_parts.append(build_paragraph(
            [{'bold': bold, 'size': size, 'italic': italic, 'underline': underline}],
            item.get('text', ''),
            item.get('alignment'),
            item.get('space_before', 0),
            item.get('space_after', item.get('space_after', 6))
        ))

doc_xml_parts.append('</w:document>')

# 构建 styles.xml
styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPrDefault>
        <w:rPr>
          <w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体" w:cs="宋体"/>
          <w:sz w:val="22"/>
        </w:rPr>
      </w:rPrDefault>
    </w:rPrDefault>
    <w:pPrDefault/>
  </w:docDefaults>
</w:styles>'''

# 构建 _rels/.rels
rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="word/styles.xml"/>
</Relationships>'''

# 构建 word/_rels/document.xml.rels
doc_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'''

# 构建 [Content_Types].xml
content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''

# ---------- 打包 zip ----------
with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('[Content_Types].xml', content_types)
    zf.writestr('_rels/.rels', rels_xml)
    zf.writestr('word/_rels/document.xml.rels', doc_rels_xml)
    zf.writestr('word/document.xml', '\n'.join(doc_xml_parts))
    zf.writestr('word/styles.xml', styles_xml)

print(f"✅ Word 文档已生成: {OUTPUT}")
print(f"   文件大小: {os.path.getsize(OUTPUT)} bytes")
