"""Build-time sanitization and link/term conversion; never runs upstream code."""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import unquote, urljoin, urlsplit, parse_qs

from bs4 import BeautifulSoup, NavigableString
import nh3
import tinycss2
from PIL import ImageColor

from .wiki_store import SOURCE, page_url, source_url, title_key

TAGS = set('a abbr b blockquote br caption code col colgroup dd del details div dl dt em figcaption figure h1 h2 h3 h4 h5 h6 hr i img kbd li mark ol p pre s small span strong sub summary sup table tbody td tfoot th thead tr u ul math semantics annotation mrow mi mn mo mfrac msup msub msubsup msqrt mroot mstyle mspace mtext mover munder munderover mtable mtr mtd mfenced'.split())
ATTRS = {'*': {'class', 'id', 'title', 'lang', 'dir'},
         'a': {'href'}, 'img': {'src', 'alt', 'width', 'height', 'loading', 'decoding'},
         'td': {'colspan', 'rowspan', 'headers', 'data-sort-value'},
         'th': {'colspan', 'rowspan', 'headers', 'scope', 'data-sort-type'},
         'ol': {'start'}, 'li': {'value'}, 'col': {'span'},
         'div': {'tabindex', 'role', 'aria-label'}, 'details': {'open'},
         'math': {'display', 'xmlns'}, 'annotation': {'encoding'},
         'mo': {'stretchy', 'fence', 'separator'}, 'mspace': {'width'},
         'mstyle': {'displaystyle', 'scriptlevel', 'mathvariant'}}
CLEANER = nh3.Cleaner(tags=TAGS, attributes=ATTRS,
    clean_content_tags={'script','style','iframe','object','embed','form','input','button','textarea','select','svg'},
    url_schemes={'http','https'}, link_rel='noopener noreferrer', strip_comments=True)
CSS_PROPERTIES = set('text-align vertical-align font-size font-weight font-style text-decoration white-space color background-color border border-top border-bottom border-left border-right border-color border-width border-style border-collapse border-spacing padding padding-top padding-bottom padding-left padding-right margin margin-top margin-bottom margin-left margin-right width min-width max-width height max-height list-style-type'.split())
COLOR = re.compile(r'(?:#[a-fA-F0-9]{3,8}|[a-zA-Z]+|rgba?\([\d.,%\s]+\))\Z')
VALUE = re.compile(r'[a-zA-Z0-9#.,%\s()/+\-]+\Z')


def term_catalog(path):
    document = json.loads(path.read_text(encoding='utf-8'))
    terms = {}
    for entry in document['entries'].values():
        en = entry.get('source', '').strip()
        zh = entry.get('translation', '').strip()
        if (entry.get('status') != 'reviewed' or not 2 <= len(en) <= 70
                or len(en.split()) > 8 or not re.search(r'[\u3400-\u9fff]', zh)
                or any(c in en+zh for c in '<>[]{}%\n\r')
                or en.endswith(('.', '!', '?', ':')) or title_key(en)=='name'):
            continue
        contexts = entry.get('contexts', [])
        if not any(c.get('reason') in ('visible_field', 'visible_name_or_term') for c in contexts):
            continue
        terms[title_key(en)] = (en, zh)
    return terms, {'game_version': document.get('source_game', ''),
                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'reviewed_terms': len(terms)}


def translated_title(title, terms):
    lookup = terms.get(title_key(title))
    if lookup:
        return lookup[1]
    if title.startswith('Named '):
        lookup = terms.get(title_key(title[6:]))
        if lookup:
            return '红装：' + lookup[1]
    if title.startswith('Category:'):
        lookup = terms.get(title_key(title[9:]))
        if lookup:
            return lookup[1]
    # These are encyclopedia navigation labels, not alternate game translations.
    return {'Battle Brothers Wiki': '战场兄弟百科', 'Character Backgrounds': '人物背景',
        'Named and Legendary Items': '红装与传奇装备', 'Origins': '起源',
        'Traits': '人物特性', 'Skills': '技能', 'Game Mechanics': '游戏机制',
        'Game Guide': '游戏指南', 'Events': '事件', 'Contracts': '委托',
        'Factions and Relations': '阵营与关系', 'Legendary locations': '传奇地点',
        'Melee Weapons': '近战武器', 'Ranged Weapons': '远程武器', 'Armor': '护甲',
        'Headgear': '头部装备', 'Shields': '盾牌', 'Retinue': '随从',
        'Crafting': '制作', 'Trophies': '战利材料', 'Injuries': '伤病',
        'Level and Experience': '等级与经验', 'Settlements': '定居点'}.get(title, '')


def style_class(style, styles):
    declarations = []
    for declaration in tinycss2.parse_declaration_list(style, skip_comments=True, skip_whitespace=True):
        if declaration.type != 'declaration' or declaration.important:
            continue
        prop = declaration.lower_name
        value = tinycss2.serialize(declaration.value).strip()
        if prop == 'background' and COLOR.fullmatch(value):
            prop = 'background-color'
        if prop not in CSS_PROPERTIES or not VALUE.fullmatch(value) or len(value) > 100:
            continue
        if any(x in value.lower() for x in ('url', 'expression', 'var(', 'attr(', 'javascript', 'transparent')):
            continue
        if '(' in value and not COLOR.fullmatch(value):
            continue
        if prop in ('color','background-color'):
            try:
                rgb=ImageColor.getrgb(value)[:3]
                brightness=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]
                if prop=='background-color' and brightness<110:value='#f1e7d3'
                if prop=='color' and brightness>135:
                    value='#'+''.join(f'{round(c*.48):02x}' for c in rgb)
            except ValueError:
                pass
        declarations.append(f'{prop}:{value}')
    if not declarations:
        return ''
    css = ';'.join(declarations)
    name = 'ws-' + hashlib.sha256(css.encode()).hexdigest()[:16]
    styles[name] = css
    return name


def local_link(href, current_title, available, asset_names, issues):
    if href.startswith('#'):
        return '#w-' + unquote(href[1:])
    full = urljoin(source_url(current_title), href)
    url = urlsplit(full)
    if url.scheme not in ('http','https'):
        return None
    if url.hostname not in ('battlebrothers.fandom.com','battlebrothers.wikia.com'):
        return full
    target = ''
    if url.path.startswith('/wiki/'):
        target = unquote(url.path[6:]).replace('_',' ')
    elif url.path == '/index.php':
        target = parse_qs(url.query).get('title', [''])[0].replace('_', ' ')
    if target:
        canonical=available.get(target) or available.get(title_key(target))
        if canonical:
            return page_url(canonical, 'w-'+unquote(url.fragment) if url.fragment else '')
        if target.startswith('File:'):
            asset=asset_names.get(target[5:]) or asset_names.get(title_key(target[5:]))
            if asset and asset.get('local_name'):return '/wiki/media/' + asset['local_name']
        if not target.startswith(('Special:', 'User:', 'User talk:', 'Talk:', 'Forum:', 'Message Wall:', 'Battle Brothers Wiki:')):
            issues.add(target)
            if not target.startswith('User blog:'):
                return page_url(target,'w-'+unquote(url.fragment) if url.fragment else '')
    return full


def image_title(tag):
    value = tag.get('data-image-name') or tag.get('data-image-key')
    if value:
        return value.replace('_',' ')
    for attr in ('data-src', 'src'):
        url = urlsplit(tag.get(attr, ''))
        match = re.search(r'/images/(?:[^/]+/){2}([^/]+)', url.path)
        if match:
            return unquote(match.group(1)).replace('_',' ')
    return ''


def render_article(parsed, terms, available, assets, styles):
    soup = BeautifulSoup(parsed.get('text', ''), 'html.parser')
    missing_links, missing_images, external_media, page_terms = set(), set(), set(), {}
    # MediaWiki supplies native MathML and a duplicate remote image fallback.
    for math_container in soup.select('.mwe-math-element'):
        math = math_container.find('math')
        if math:
            math.extract()
            math.attrs = {'display': math.get('display','inline')}
            math_container.clear()
            math_container.append(math)
    for bad in soup.find_all(['script','style','iframe','object','embed','form','input','button','textarea','select','svg']):
        if bad.name == 'iframe' and bad.get('src','').startswith(('http://','https://')):
            link = soup.new_tag('a', href=bad['src'])
            link.string = '查看原文引用的视频'
            bad.replace_with(link)
        else:
            bad.decompose()
    for element in soup.find_all(True):
        original_classes = element.get('class', [])
        element['class'] = ['w-'+c for c in original_classes if re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',c)]
        if element.get('id'):
            element['id'] = 'w-' + element['id']
        original_style = element.get('style', '')
        if 'color: transparent' in original_style or 'color:transparent' in original_style:
            element['class'].append('w-sort-label')
        cls = style_class(original_style, styles)
        if cls:
            element['class'].append(cls)
        element.attrs.pop('style', None)
        if element.name == 'a':
            href = local_link(element.get('href',''), parsed['title'], available, assets, missing_links)
            if href:
                element['href'] = href
            else:
                element.attrs.pop('href',None)
        if element.name == 'img':
            title = image_title(element)
            asset = assets.get(title) or assets.get(title_key(title))
            if asset and asset.get('mime','').startswith('video/'):
                external_media.add(title)
                replacement = soup.new_tag('a',href=asset.get('description_url') or source_url('File:'+title))
                replacement.string = '查看视频：' + title
                element.replace_with(replacement)
                continue
            if asset and asset.get('local_name'):
                element['src'] = '/wiki/media/' + asset['local_name']
                element['loading'] = 'lazy'
                element['decoding'] = 'async'
                element['title'] = title
                term = terms.get(title_key(element.get('alt','')))
                if term:
                    element['title'] = f'{term[1]} / {term[0]}'
                    page_terms[term[0]] = term[1]
            else:
                if title:
                    missing_images.add(title)
                replacement = soup.new_tag('span')
                replacement['class'] = ['w-missing-image']
                replacement['title'] = '原图待补充：' + (title or element.get('alt',''))
                replacement.string = element.get('alt') or title or '图片'
                element.replace_with(replacement)
                continue
            for attr in ('width', 'height'):
                value = str(element.get(attr, ''))
                if not value.isdigit() or not 1 <= int(value) <= 4096:
                    element.attrs.pop(attr, None)
        if element.name in ('td','th'):
            for attr in ('colspan','rowspan'):
                value = str(element.get(attr,''))
                if not value.isdigit() or not 1 <= int(value) <= 1000:
                    element.attrs.pop(attr,None)
    # Plain English text is retained. Only exact, reviewed names gain a second label.
    for text in list(soup.find_all(string=True)):
        if not isinstance(text,NavigableString) or text.parent is None:
            continue
        if text.find_parent(['math','code','pre','annotation']):
            continue
        value = str(text).strip()
        term = terms.get(title_key(value)) if len(value) <= 80 else None
        if term and value:
            span = soup.new_tag('span')
            span['class'] = ['w-term']
            en = soup.new_tag('span'); en['class'] = ['w-term-en']; en.string = str(text)
            zh = soup.new_tag('span'); zh['class'] = ['w-term-zh']; zh.string = term[1]
            span.append(en); span.append(zh); text.replace_with(span)
            page_terms[term[0]] = term[1]
    for table in soup.find_all('table'):
        if table.find_parent('table'):
            continue
        wrapper = soup.new_tag('div', tabindex='0')
        wrapper['role'] = 'region'; wrapper['aria-label'] = '资料表格，可横向滚动'
        wrapper['class'] = ['w-table-scroll']
        table.wrap(wrapper)
    html = CLEANER.clean(str(soup))
    plain = soup.get_text(' ', strip=True)
    sections = []
    for section in parsed.get('sections', []):
        sections.append({'level':str(section.get('level','2')),
                         'title':BeautifulSoup(section.get('line',''),'html.parser').get_text(),
                         'anchor':'w-'+section.get('anchor','')})
    return {'html':html, 'plain':plain, 'sections':sections, 'terms':page_terms,
            'missing_links':sorted(missing_links), 'missing_images':sorted(missing_images),
            'external_media':sorted(external_media)}
