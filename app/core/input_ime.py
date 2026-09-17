"""Minimal input-method fix against the checked official input control."""
import hashlib

ORIGINAL_SHA256 = 'adaa798d5b0fa81ef89cff846a460469a7f5df7ced4dc20e72e77f5d685658c4'
ENTRY = 'ui/controls/input.js'


def patch_input(raw: bytes) -> bytes:
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('游戏输入控件与支持的原版不一致，未修改。')
    text = raw.decode('utf-8')
    anchor = '        // allow only special keys'
    ime = ('        // BBMOD: let the IME finish composing before counting characters.\r\n'
           '        if (code === 229 || (_event.originalEvent && _event.originalEvent.isComposing))\r\n'
           '        {\r\n            return true;\r\n        }\r\n\r\n')
    tail = "    result.data('input', data);"
    notify = ("    result.on('input.bbmod compositionend.bbmod', function ()\r\n"
              "    {\r\n"
              "        if (_inputUpdatedCallback !== undefined && jQuery.isFunction(_inputUpdatedCallback))\r\n"
              "        {\r\n"
              "            _inputUpdatedCallback($(this), $(this).getInputTextLength());\r\n"
              "        }\r\n"
              "    });\r\n\r\n")
    if text.count(anchor) != 1 or text.count(tail) != 1:
        raise ValueError('游戏输入控件结构不受支持。')
    return text.replace(anchor, ime + anchor).replace(tail, notify + tail).encode('utf-8')
