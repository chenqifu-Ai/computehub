#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 联合体内部授权书 .docx — using triple-quoted strings to avoid quote hell"""
import zipfile, os, re

OUTPUT = '/root/.openclaw/workspace/ai_agent/results/霞浦EOD项目_联合体授权书.docx'

def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def P(text, bold=False, sz=None, color=None, sb=None, sa=None, align=None):
    """Build a paragraph XML string"""
    segs = re.split(r'(\*\*[^*]+\*\*)', text)
    runs = []
    for seg in segs:
        if seg.startswith('**') and seg.endswith('**'):
            runs.append(R(seg[2:-2], True, sz, None))
        else:
            runs.append(R(seg, bold, sz, color))
    rx = ''.join(runs)
    alx = f'<w:jc w:val="{align}"/>' if align else ''
    bf = f' w:before="{sb}"' if sb is not None else ''
    af = f' w:after="{sa}"' if sa is not None else ''
    return f'<w:p><w:pPr><w:spacing{af}{bf} w:line="360" w:lineRule="auto"/>{alx}</w:pPr>{rx}</w:p>'

def R(text, bold=False, sz=None, color=None):
    if not text: return ''
    t = esc(text)
    props = []
    if bold: props.append('<w:b/>')
    if sz: props.append(f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>')
    if color: props.append(f'<w:color w:val="{color}"/>')
    px = f'<w:rPr>{"".join(props)}</w:rPr>' if props else ''
    return f'<w:r>{px}<w:t xml:space="preserve">{t}</w:t></w:r>'

def H(text, level=1):
    szs = {0:36,1:32,2:28,3:26,4:24}
    return P(text, bold=True, sz=szs.get(level,28), sb=200, sa=120)

def L():
    return '<w:p><w:pPr><w:spacing w:after="0" w:before="0"/></w:pPr></w:p>'

def DIV():
    return P('\u2501' * 60, sz=16, color='999999', align='center')

# ===== Build the document parts =====

parts = []

parts.append(P('合同编号：ZCHT-EOD-2026-001', sz=20, color='666666', align='right'))
parts.append(L())
parts.append(H('霞浦县美丽海湾建设与产业一体化开发\uff08EOD\uff09项目', level=1))
parts.append(H('联合体内部授权书', level=0))
parts.append(L())
parts.append(P('签订日期：2026年____月____日', sz=22))
parts.append(P('签订地点：福建省厦门市', sz=22))
parts.append(L())
parts.append(DIV())
parts.append(L())

# 联合体成员
parts.append(H('联合体成员', level=2))
parts.append(L())

# Table-like header
headers = ['角色', '公司名称', '统一社会信用代码', '法定代表人']
data = [
    ('牵头方', '中财海绵城市基金管理(深圳)有限公司'),
    ('成员一', '福建建工集团有限责任公司'),
    ('成员二', '福州合立道建筑设计有限公司'),
    ('成员三', '宁德市东侨经济开发区闽益农农业科技有限公司'),
]

parts.append(P('  |  '.join(headers), bold=True, sz=20))
parts.append(P('--- | --- | --- | ---', sz=16, color='999999'))
for role, name in data:
    parts.append(P(f'{role}  |  {name}  |  __________  |  ________', sz=20))
parts.append(L())
parts.append(P('（以下简称"全体联合体成员"）', sz=20))
parts.append(L())

# 鉴于
parts.append(H('鉴于', level=2))
parts.append(L())
parts.append(P('\u3000\u30001\u3001宁德市霞浦生态环境局就\u201c霞浦县美丽海湾建设与产业一体化开发（EOD）项目\u201d（以下简称\u201c本项目\u201d）于2026年5月18日向全体联合体成员发出《霞浦县美丽海湾建设与产业一体化开发(EOD)项目投资合作协议》（以下简称\u201c主协议\u201d）；', sz=22))
parts.append(P('\u3000\u30002\u3001全体联合体成员拟共同参与本项目的投资、建设及运营，并已就合作事宜达成初步共识；', sz=22))
parts.append(P('\u3000\u30003\u3001为便于对外沟通协调及推进项目履约，全体联合体成员同意授权牵头方代表联合体统一行使相关权利、履行相关义务。', sz=22))
parts.append(L())
parts.append(P('全体联合体成员不可撤销地授权牵头方\u201c中财海绵城市基金管理(深圳)有限公司\u201d在以下事项范围内代表联合体行使权利、履行义务：', sz=22, bold=True))
parts.append(L())

# 第一条
parts.append(H('第一条 对外沟通与函件往来', level=2))
for n, t in enumerate(['以联合体名义向宁德市霞浦生态环境局及项目相关方发送函件、申请、报告等书面文件；',
  '包括但不限于：《关于申请调整霞浦县美丽海湾建设与产业一体化开发(EOD)项目投资合作协议生效日期的函》的签发与送达；',
  '接收项目相关方发送给联合体的全部通知、函件及文件。'], 1):
    parts.append(P(f'\u3000\u30001.{n} {t}', sz=22))
parts.append(L())

# 第二条
parts.append(H('第二条 协议签署与变更', level=2))
parts.append(P('\u3000\u30002.1 代表联合体签署主协议及与主协议相关的补充协议、变更协议；', sz=22))
parts.append(P('\u3000\u30002.2 就主协议生效日期调整、履约期限变更等事项与宁德市霞浦生态环境局进行协商并达成一致；', sz=22))
parts.append(P('\u3000\u30002.3 但以下事项除外：', sz=22))
for n, t in enumerate(['涉及联合体成员内部权利义务分配的重大变更；',
  '主协议项下总投资额增减超过原总投资额10%的变更；',
  '联合体成员退出或新增成员的变更。'], 1):
    parts.append(P(f'\u3000\u3000\u3000（{n}）{t}', sz=22))
parts.append(P('\u3000\u3000上述除外事项须经全体联合体成员另行书面一致同意。', sz=22))
parts.append(L())

# 第三条
parts.append(H('第三条 履约协调', level=2))
parts.append(P('\u3000\u30003.1 协调各成员按主协议约定完成各自分工；', sz=22))
parts.append(P('\u3000\u30003.2 牵头方就履约过程中的常规事项（非重大变更）可代表联合体作出决定，但应在作出决定后5个工作日内书面通知其他成员；', sz=22))
parts.append(P('\u3000\u30003.3 牵头方应每季度向全体成员书面通报项目履约进展情况。', sz=22))
parts.append(L())

# 第四条
parts.append(H('第四条 资金与财务管理', level=2))
parts.append(P('\u3000\u30004.1 牵头方负责与项目业主方就项目资金拨付、费用结算等事宜进行对接；', sz=22))
parts.append(P('\u3000\u30004.2 各成员按其在联合体内部约定的比例和方式承担出资义务、分配收益；', sz=22))
parts.append(P('\u3000\u3000**4.3 具体资金安排、出资比例、收益分配方式由全体联合体成员另行签订《联合体合作协议》另行约定。**', sz=22))
parts.append(L())

# 第五条
parts.append(H('第五条 授权期限', level=2))
parts.append(P('\u3000\u3000本授权书自全体联合体成员签章之日起生效，有效期至以下任一情形发生之日止（以较早者为准）：', sz=22))
for n, t in enumerate(['主协议履行完毕之日；', '主协议依法解除或终止之日；', '全体联合体成员书面同意撤销本授权之日。'], 1):
    parts.append(P(f'\u3000\u3000\u3000（{n}）{t}', sz=22))
parts.append(L())

# 第六条
parts.append(H('第六条 保密义务', level=2))
parts.append(P('\u3000\u3000各联合体成员对本项目相关的全部信息（包括但不限于主协议内容、项目技术资料、商务条件、各成员内部信息等）负有保密义务，未经全体成员书面同意，不得向任何第三方披露，法律法规另有规定的除外。', sz=22))
parts.append(L())

# 第七条
parts.append(H('第七条 法律效力', level=2))
items7 = [
    '本授权书是全体联合体成员真实意思表示，对各方具有法律约束力。',
    '本授权书一式五份，牵头方持两份，其他各成员各持一份，具有同等法律效力。',
    '本授权书未尽事宜，由全体联合体成员另行协商解决。',
    '因本授权书引起的或与本授权书有关的任何争议，各方应友好协商解决；协商不成的，任何一方均可向牵头方所在地有管辖权的人民法院提起诉讼。'
]
for n, t in enumerate(items7, 1):
    parts.append(P(f'\u3000\u30007.{n} {t}', sz=22))
parts.append(L())

parts.append(DIV())
parts.append(L())
parts.append(P('（以下无正文）', sz=20, color='666666', align='center'))
parts.append(L())

# 签署页
parts.append(P('签署页', bold=True, sz=28, align='center'))
parts.append(L())

sig_names = [
    ('牵头方', '中财海绵城市基金管理(深圳)有限公司'),
    ('成员一', '福建建工集团有限责任公司'),
    ('成员二', '福州合立道建筑设计有限公司'),
    ('成员三', '宁德市东侨经济开发区闽益农农业科技有限公司'),
]
for role, name in sig_names:
    parts.append(L())
    parts.append(P(f'{role}（盖章）：', bold=True, sz=24))
    parts.append(P(name, sz=22))
    parts.append(L())
    parts.append(P('法定代表人或授权代表签字：____________', sz=22))
    parts.append(P('日期：______年____月____日', sz=22))
    parts.append(L())

# ===== Build the document =====

BODY = ''.join(parts)

document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <w:body>
        {BODY}
        <w:sectPr>
            <w:pgSz w:w="11906" w:h="16838"/>
            <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708"/>
        </w:sectPr>
    </w:body>
</w:document>'''

with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    zf.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    zf.writestr('word/document.xml', document_xml.encode('utf-8'))
    zf.writestr('word/_rels/document.xml.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    zf.writestr('word/styles.xml', '<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:styleId="Normal" w:default="1"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/><w:rFonts w:ascii="宋体" w:hAnsi="宋体"/></w:rPr></w:style></w:styles>')

print(f'\u2705 \u5df2\u751f\u6210: {OUTPUT}')
fsize = os.path.getsize(OUTPUT)
print(f'\u6587\u4ef6\u5927\u5c0f: {fsize/1024:.1f} KB')
