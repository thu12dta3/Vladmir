
import html
import re

STYLESHEET = """
QMainWindow, #appRoot, #contentArea { background: #121212; }
QWidget { color: #e8e8e8; font-family: Inter, "Noto Sans", sans-serif; font-size: 13px; }
QLabel { background: transparent; }
#sidebarScroll, #sidebar { background: #181818; border: 0; }
#sidebarScroll { border-right: 1px solid #2b2b2b; }
#brand { color: #f3f3f3; font-size: 21px; font-weight: 750; letter-spacing: 2.4px; }
#brandCaption { color: #878787; font-size: 9px; letter-spacing: 1.8px; margin-top: 3px; }
#title { color: #f3f3f3; font-size: 21px; font-weight: 650; }
#connectionStatus { color: #949494; font-size: 11px; }
#headerDivider { background: #2b2b2b; border: 0; }
#welcomeEyebrow { color: #a7a7a7; font-size: 10px; font-weight: 650; letter-spacing: 1.6px; }
#welcomeTitle { color: #f1f1f1; font-size: 31px; font-weight: 620; letter-spacing: -0.5px; }
#welcomeHint { color: #9d9d9d; font-size: 14px; }
#engineerHero { background: #1d1d1d; border: 1px solid #3b3b3b; border-radius: 15px; }
#engineerCardTitle { color: #eeeeee; font-size: 16px; font-weight: 650; }
#engineerModelStatus { color: #b0b0b0; font-size: 12px; }
#engineerModelIndicator { color: #d4d4d4; background: #2b2b2b; border: 1px solid #454545; border-radius: 10px; padding: 6px 9px; font-size: 10px; font-weight: 750; letter-spacing: 0.6px; }
#engineerModelIndicator[ready="true"] { color: #dbdbdb; background: #2e2e2e; border-color: #4e4e4e; }
#engineerSectionTitle { color: #e5e5e5; font-size: 14px; font-weight: 650; margin-top: 5px; }
#engineerHint { color: #9c9c9c; font-size: 11px; }
#engineerStepCard { background: #1b1b1b; border: 1px solid #333333; border-radius: 12px; }
#engineerStepNumber { color: #a0a0a0; font-size: 10px; font-weight: 750; letter-spacing: 1px; }
#engineerStepTitle { color: #e7e7e7; font-size: 14px; font-weight: 650; }
#engineerQuickAction { background: #222222; border: 1px solid #3a3a3a; border-radius: 10px; color: #dfdfdf; text-align: left; padding: 10px 12px; }
#engineerQuickAction:hover { background: #2c2c2c; border-color: #5e5e5e; }
#engineerMissionSummary { color: #afafaf; background: #1c1c1c; border: 1px solid #333333; border-radius: 9px; padding: 9px 12px; font-size: 11px; }
#engineerBadge { color: #e0e0e0; background: #2f2f2f; border: 1px solid #4c4c4c; border-radius: 10px; padding: 6px 9px; font-size: 9px; font-weight: 750; letter-spacing: 0.8px; }
#engineerWorkFeedback { background: #1c1c1c; border: 1px solid #404040; border-radius: 10px; }
#engineerWorkLabel { color: #d8d8d8; font-size: 11px; font-weight: 600; }
#engineerWorkBar { border: none; background: #2e2e2e; border-radius: 2px; }
#engineerWorkBar::chunk { background: #b7b7b7; border-radius: 2px; }
#evolutionProgress { border: 1px solid #333333; background: #1c1c1c; border-radius: 7px; color: #cacaca; text-align: center; font-size: 10px; }
#evolutionProgress::chunk { background: #9a9a9a; border-radius: 6px; }
#muted, #footer { color: #898989; }
#footer { font-size: 10px; }
#section { color: #797979; font-size: 9px; font-weight: 750; letter-spacing: 1.2px; margin: 2px 0 4px 7px; }
#statusBox { background: #1e1e1e; border: 1px solid #2d2d2d; border-radius: 9px; }
#statusTitle { color: #929292; font-size: 10px; font-weight: 550; }
#statusValue { color: #dfdfdf; font-size: 10px; font-weight: 600; }
QPushButton, QToolButton { background: #242424; border: 1px solid #373737; border-radius: 10px; padding: 8px 12px; font-weight: 550; }
QPushButton:hover, QToolButton:hover { background: #2d2d2d; border-color: #4d4d4d; }
QPushButton:pressed, QToolButton:pressed { background: #363636; }
QPushButton:focus, QToolButton:focus { border-color: #bbbbbb; }
QPushButton:disabled { color: #707070; background: #1d1d1d; border-color: #2b2b2b; }
#navButton { background: transparent; border: 1px solid transparent; color: #b1b1b1; text-align: left; padding: 4px 9px; font-size: 12px; }
#navButton:hover { background: #242424; border-color: #2f2f2f; color: #f0f0f0; }
#navButtonActive { background: #2e2e2e; border: 1px solid #5c5c5c; color: #f2f2f2; text-align: left; padding: 7px 10px; font-size: 12px; }
#toolsButton { background: transparent; border: 1px solid transparent; color: #bababa; text-align: left; padding: 5px 9px; }
#toolsButton:hover { background: #242424; border-color: #2f2f2f; color: #f0f0f0; }
#toolsButton::menu-indicator { subcontrol-origin: padding; subcontrol-position: right center; right: 8px; }
#secondaryButton { background: transparent; color: #949494; border: 1px solid transparent; text-align: left; padding: 7px 8px; font-size: 11px; }
#secondaryButton:hover { color: #e4e4e4; background: #242424; border-color: #363636; }
#headerAction { background: #262626; color: #e9e9e9; border: 1px solid #3c3c3c; padding: 8px 14px; }
#headerAction:hover { background: #323232; }
#modelSelector { background: #222222; border: 1px solid #393939; border-radius: 10px; padding: 7px 10px; min-width: 170px; font-size: 12px; }
#modelSelector:hover { border-color: #636363; }
#chatSelector { background: #222222; border: 1px solid #393939; border-radius: 9px; padding: 6px 9px; min-width: 185px; font-size: 11px; }
#chatSelector:hover { border-color: #636363; }
#reasoningSelector { background: #222222; border: 1px solid #393939; border-radius: 10px; padding: 7px 8px; min-width: 95px; font-size: 12px; }
#reasoningSelector:hover { border-color: #636363; }
QComboBox::drop-down { border: 0; width: 19px; }
QComboBox QAbstractItemView { background: #222222; border: 1px solid #454545; selection-background-color: #3e3e3e; }
#iconButton { background: transparent; border: 1px solid transparent; border-radius: 9px; padding: 4px; min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px; }
#iconButton:hover { background: #242424; border-color: #393939; }
#suggestionCard { background: #1c1c1c; color: #d8d8d8; border: 1px solid #323232; text-align: left; padding: 14px 16px; border-radius: 13px; font-size: 13px; }
#suggestionCard:hover { background: #262626; color: #f4f4f4; border-color: #595959; }
#chatScroll, #chatContent { background: transparent; border: 0; }
#composerBox { background: #1d1d1d; border: 1px solid #3c3c3c; border-radius: 19px; }
#composerBox:hover { border-color: #4d4d4d; }
#composerBox[dropActive="true"] { background: #262626; border: 2px solid #9a9a9a; }
#messageInput { background: transparent; border: 0; color: #eeeeee; padding: 3px 1px; selection-background-color: #4b4b4b; font-size: 15px; }
#composerHint { color: #797979; font-size: 10px; }
#attachButton { background: transparent; border: 1px solid transparent; color: #ababab; padding: 6px 7px; font-size: 12px; }
#attachButton:hover { background: #2b2b2b; color: #eeeeee; border-color: #404040; }
#attachmentList { background: #1a1a1a; border: 1px solid #373737; border-radius: 9px; padding: 4px; }
#attachmentList::item { padding: 5px 8px; border-radius: 6px; }
#attachmentList::item:selected { background: #3c3c3c; color: #f0f0f0; }
#sendButton { background: #9a9a9a; color: #151515; border: 0; border-radius: 12px; padding: 0; min-width: 40px; max-width: 40px; min-height: 40px; max-height: 40px; }
#sendButton:hover { background: #b7b7b7; }
#sendButton:disabled { background: #585858; }
#userBubble { background: #262626; border: 1px solid #373737; border-radius: 17px; }
#assistantBubble { background: #1d1d1d; border: 1px solid #2f2f2f; border-radius: 17px; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 3px 0; }
QScrollBar::handle:vertical { background: #3e3e3e; border-radius: 3px; min-height: 32px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLineEdit, QPlainTextEdit { background: #1c1c1c; border: 1px solid #3b3b3b; border-radius: 9px; padding: 8px; selection-background-color: #4b4b4b; }
QLineEdit:focus, QPlainTextEdit:focus { border-color: #7b7b7b; }
QDialog { background: #121212; }
QMenu { background: #1e1e1e; color: #e2e2e2; border: 1px solid #3d3d3d; padding: 6px; }
QMenu::item { padding: 8px 18px; border-radius: 5px; }
QMenu::item:selected { background: #373737; color: #f5f5f5; }
QMenu::separator { height: 1px; background: #373737; margin: 5px 8px; }
#libraryHint { color: #9b9b9b; font-size: 12px; }
QComboBox { background: #1c1c1c; border: 1px solid #3b3b3b; border-radius: 9px; padding: 7px; color: #e1e1e1; }
#libraryDrop { background: #1d1d1d; border: 1px dashed #6a6a6a; border-radius: 13px; color: #dfdfdf; padding: 18px; }
QTableWidget { background: #191919; alternate-background-color: #1f1f1f; border: 1px solid #373737; gridline-color: #2f2f2f; selection-background-color: #3b3b3b; }
QHeaderView::section { background: #222222; color: #c8c8c8; padding: 8px; border: 0; border-bottom: 1px solid #3e3e3e; }
QProgressBar { background: #191919; border: 1px solid #373737; border-radius: 5px; text-align: center; min-height: 16px; }
QProgressBar::chunk { background: #898989; border-radius: 4px; }
"""


def safe_web_link(url):
    from urllib.parse import urlsplit
    if not isinstance(url,str) or len(url)>4096 or any(ord(c)<33 for c in url) or '\\' in url:return False
    try:
        parts=urlsplit(url)
        return parts.scheme in ('http','https') and bool(parts.hostname) and not parts.username and not parts.password
    except ValueError:return False

def inline_html(text):
    pattern=re.compile(r'`([^`\n]+)`|\[([^\]\n]+)\]\((https?://[^\s<>]+)\)|(https?://[^\s<>]+)')
    result=[];start=0
    def plain(value):return re.sub(r'\*\*([^*\n]+)\*\*',r'<b>\1</b>',html.escape(value)).replace('\n','<br>')
    for match in pattern.finditer(text):
        result.append(plain(text[start:match.start()]));start=match.end()
        if match.group(1):result.append('<span style="color:#dddddd; font-family:monospace;">'+html.escape(match.group(1))+'</span>');continue
        label=match.group(2);url=match.group(3) or match.group(4);suffix=''
        if not label:
            trimmed=url.rstrip('.,;!?')
            while trimmed.endswith(')') and trimmed.count(')')>trimmed.count('('):trimmed=trimmed[:-1]
            suffix=url[len(trimmed):];url=trimmed;label=url
        if safe_web_link(url):result.append('<a href="'+html.escape(url,quote=True)+'" style="color:#eeeeee; text-decoration:underline;">'+html.escape(label)+'</a>'+plain(suffix))
        else:result.append(plain(match.group(0)))
    result.append(plain(text[start:]));return ''.join(result)

def message_html(text: str) -> str:

    lines=text.splitlines(); rendered=[]; paragraph=[]; list_kind=None; list_items=[]; i=0

    def flush_paragraph():
        if paragraph:
            rendered.append('<p style="margin:5px 0;">'+inline_html('\n'.join(paragraph))+'</p>')
            paragraph.clear()

    def flush_list():
        nonlocal list_kind, list_items
        if list_kind:
            tag='ol' if list_kind=='ol' else 'ul'
            rendered.append('<'+tag+' style="margin-top:4px; margin-bottom:4px;">'+''.join('<li>'+inline_html(item)+'</li>' for item in list_items)+'</'+tag+'>')
        list_kind=None;list_items=[]

    def flush_text_blocks():
        flush_paragraph();flush_list()

    def cells(line):
        return [part.strip() for part in line.strip().strip('|').split('|')]

    while i<len(lines):
        line=lines[i]
        if line.startswith('```'):
            flush_text_blocks();code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]);i+=1
            if i<len(lines):i+=1
            rendered.append('<pre style="color:#dddddd; font-family:monospace; background-color:#161616; white-space:pre-wrap;">'+html.escape('\n'.join(code))+'</pre>')
            continue
        heading=re.match(r'^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$',line)
        if heading:
            flush_text_blocks();level=min(len(heading.group(1)),4)
            rendered.append(f'<h{level} style="margin:12px 0 5px;">{inline_html(heading.group(2))}</h{level}>');i+=1;continue
        if i+1<len(lines) and '|' in line and re.match(r'^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$',lines[i+1]):
            flush_text_blocks();headers=cells(line);i+=2;rows=[]
            while i<len(lines) and '|' in lines[i] and lines[i].strip():
                rows.append(cells(lines[i]));i+=1
            table=['<table border="1" cellspacing="0" cellpadding="5" style="border-color:#484848; border-collapse:collapse; margin:8px 0;"><thead><tr>']
            table.extend('<th>'+inline_html(value)+'</th>' for value in headers)
            table.append('</tr></thead><tbody>')
            for row in rows:
                table.append('<tr>')
                for col in range(len(headers)):
                    table.append('<td>'+inline_html(row[col] if col<len(row) else '')+'</td>')
                table.append('</tr>')
            table.append('</tbody></table>');rendered.append(''.join(table));continue
        if not line.strip():
            flush_text_blocks();i+=1;continue
        if re.match(r'^\s{0,3}([-*_]\s*){3,}$',line):
            flush_text_blocks();rendered.append('<hr/>');i+=1;continue
        item=re.match(r'^\s{0,3}([-+*])\s+(.+)$',line)
        numbered=re.match(r'^\s{0,3}\d+[.)]\s+(.+)$',line)
        if item or numbered:
            flush_paragraph();kind='ul' if item else 'ol'
            if list_kind and list_kind!=kind:flush_list()
            list_kind=kind;list_items.append((item or numbered).group(2 if item else 1));i+=1;continue
        quote=re.match(r'^\s{0,3}>\s?(.*)$',line)
        if quote:
            flush_text_blocks();quoted=[]
            while i<len(lines):
                match=re.match(r'^\s{0,3}>\s?(.*)$',lines[i])
                if not match:break
                quoted.append(match.group(1));i+=1
            rendered.append('<blockquote style="margin:6px 0; padding-left:10px; border-left:2px solid #777; color:#c7c7c7;">'+inline_html('\n'.join(quoted))+'</blockquote>');continue
        flush_list();paragraph.append(line);i+=1
    flush_text_blocks()
    return '<div style="line-height:150%;">'+''.join(rendered)+'</div>'
