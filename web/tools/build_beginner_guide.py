"""Build the public and offline guides from Markdown, PNGs and exported PDF.

Run after updating BBMOD新手使用说明.md and output/pdf/BBMOD新手使用说明.pdf.
Requires markdown-it-py. No inline CSS, scripts or data images: keep the site's CSP.
"""
from pathlib import Path
import html
import re
import shutil
import base64
from markdown_it import MarkdownIt

ROOT=Path(__file__).resolve().parents[2]
VERSION='0274'
DESKTOP_VERSION=re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]",(ROOT/'app/core/version.py').read_text(encoding='utf-8'),re.M).group(1)
DESKTOP_LABEL=DESKTOP_VERSION.rsplit('-',1)[-1]
assets=ROOT/'web/static/guides'/VERSION
assets.mkdir(parents=True,exist_ok=True)
parser=MarkdownIt('commonmark',{'html':False}).enable('table')
source=(ROOT/'BBMOD新手使用说明.md').read_text(encoding='utf-8')
assert '0.27.4' in source
assert DESKTOP_VERSION in source, f'BBMOD新手使用说明.md 未提及当前桌面版本 {DESKTOP_VERSION}'
assert not any(word in source for word in ('qfile.qq.com','旧教程用户注意','傻瓜包','学习版','v0.25'))
tokens=parser.parse(source)
toc=[];images=[];count=0
for i,token in enumerate(tokens):
    if token.type=='heading_open':
        count+=1
        identity=f'guide-section-{count}'
        token.attrSet('id',identity)
        if token.tag=='h2':toc.append((identity,tokens[i+1].content))
    for child in token.children or []:
        if child.type=='image':
            path=(ROOT/child.attrGet('src')).resolve()
            assert path.is_relative_to(ROOT) and path.is_file()
            shutil.copyfile(path,assets/path.name)
            child.attrSet('src',f'/static/guides/{VERSION}/{path.name}')
            child.attrSet('loading','lazy');child.attrSet('width','1360');child.attrSet('height','880')
            images.append(path.name)
content=parser.renderer.render(tokens,parser.options,{})
content=content.replace('<table>','<div class="guide-table"><table>').replace('</table>','</table></div>')
index=content.index('<h2')
links=''.join(f'<a href="#{key}">{html.escape(label)}</a>' for key,label in toc)
content=content[:index]+'<nav class="guide-toc" aria-label="使用说明目录"><h2>按顺序开始，或跳到遇到的问题</h2><div class="guide-toc-links">'+links+'</div></nav>'+content[index:]
prefix="""{% extends 'base.html' %}{% load static %}
{% block title %}BBMOD 新手使用说明 · 阿飞起源 v0.27.4{% endblock %}
{% block extra_head %}<link rel="stylesheet" href="{% static 'beginner-guide-0274.css' %}">{% endblock %}
{% block content %}<article class="beginner-guide" id="guide-top">
<div class="guide-actions"><a class="button primary" href="{% static 'guides/0274/bbmod-beginner-guide-v0.27.4.pdf' %}" download>下载 PDF，离线照着操作</a><a class="button" href="{% url 'downloads' %}">下载 BBMOD 管理器</a><span class="guide-version">2026-10-03 官网迁移修订 · DESKTOP_LABEL / MOD v0.27.4</span></div>
""".replace('DESKTOP_LABEL',DESKTOP_LABEL)
suffix='<a class="guide-back" href="#guide-top">回到目录 ↑</a></article>{% endblock %}\n'
(ROOT/'web/templates/beginner_guide.html').write_text(prefix+content+suffix,encoding='utf-8')

# Preserve the reviewed offline document's styling and print layout while
# rebuilding its body from the same Markdown as the public guide.
offline_path=ROOT/'BBMOD新手使用说明.html'
offline_shell=offline_path.read_text(encoding='utf-8')
offline_tokens=parser.parse(source)
offline_toc=[];count=0
for i,token in enumerate(offline_tokens):
    if token.type=='heading_open':
        count+=1
        identity=f'section-{count}'
        token.attrSet('id',identity)
        if token.tag=='h2':offline_toc.append((identity,offline_tokens[i+1].content))
    for child in token.children or []:
        if child.type=='image':
            path=(ROOT/child.attrGet('src')).resolve()
            assert path.is_relative_to(ROOT) and path.is_file()
            child.attrSet('src','data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode('ascii'))
offline_content=parser.renderer.render(offline_tokens,parser.options,{})
offline_content=offline_content.replace('<table>','<div class="table-scroll"><table>').replace('</table>','</table></div>')
index=offline_content.index('<h2')
offline_links=''.join(f'<a href="#{key}">{html.escape(label)}</a>' for key,label in offline_toc)
offline_content=offline_content[:index]+'<nav aria-label="使用说明目录"><h2>按顺序开始，或跳到遇到的问题</h2><div class="toc">'+offline_links+'</div></nav>'+offline_content[index:]
offline_content+='<a class="top" href="#top">回到开头 ↑</a>'
before,body=offline_shell.split('<main>',1)
_,after=body.split('</main>',1)
offline_path.write_text(before+'<main>'+offline_content+'</main>'+after,encoding='utf-8')

shutil.copyfile(ROOT/'output/pdf/BBMOD新手使用说明.pdf',assets/'bbmod-beginner-guide-v0.27.4.pdf')
assert len(images)==4
print('Built /guide/:',len(toc),'sections,',len(images),'images, downloadable PDF.')
