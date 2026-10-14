from .tokens import MOTION

def css():
    return f'''\n@keyframes reveal{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
@keyframes growX{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes growY{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes draw{{from{{stroke-dashoffset:1}}to{{stroke-dashoffset:0}}}}
@keyframes flow{{from{{stroke-dashoffset:0}}to{{stroke-dashoffset:-36}}}}
@keyframes breathe{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
.reveal{{opacity:0;animation:reveal {MOTION['reveal']}ms cubic-bezier(.22,1,.36,1) forwards}}
.bar-x{{transform-box:fill-box;transform-origin:left;animation:growX {MOTION['scene']}ms cubic-bezier(.22,1,.36,1) forwards}}
.bar-y{{transform-box:fill-box;transform-origin:bottom;animation:growY {MOTION['scene']}ms cubic-bezier(.22,1,.36,1) forwards}}
.trace{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw {MOTION['scene']}ms cubic-bezier(.22,1,.36,1) forwards}}
.flow{{stroke-dasharray:8 10;animation:flow {MOTION['ambient']}ms linear infinite}}
.signal{{animation:breathe {MOTION['ambient']}ms ease-in-out infinite}}
@media (prefers-reduced-motion: reduce){{
 .reveal,.bar-x,.bar-y,.trace,.flow,.signal{{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}}
}}
'''