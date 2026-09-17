# Place-name display session (Steam 1.5.2.3, x86)

This adapter changes display strings only. The game executable on disk must
have SHA-256 `345126b48b57719e71c80cd21b778f1a0bfda52295cc136ce3895ef43bbafd6a`.
The launcher passes the installed package's hashed UTF-8 dictionary to its
child process. No registry value, environment setting on the host, save field,
game script name, or persistent language-mode file is written.

## Native interfaces

These addresses and conventions were read from the previously captured mapped
image of the supported executable, without launching the game. Addresses are
RVAs, not absolute pointers. The image used for the audit has base `0x30000`.

| Routine | RVA | Arguments | Stack cleanup |
| --- | --- | --- | --- |
| Original `getroottable` native callback | `0x19f070` | VM on stack, cdecl | Caller |
| `sq_pushstring` | `0x185ca0` | VM in ECX, string in EDX, length on stack | Caller, 4 bytes |
| `sq_newslot` | `0x1870f0` | VM in ECX, index in EDX, static flag on stack | Caller, 4 bytes |
| VM `Pop` | `0x190910` | VM in ECX, count on stack, thiscall | Callee, 4 bytes |

The optimized internal register conventions cannot be expressed by simply
declaring the first two interfaces `__fastcall`: that would remove stack
arguments twice. `place_session.h` uses explicit x86 wrappers. The separate
test executable supplies mock callees with these exact conventions and checks
the stack pointer and Squirrel stack after repeated calls and error cases.

The root callback uses VM fields: stack data `+0x18`, initialized stack size
`+0x1c`, top `+0x24`, stack base `+0x28`, root object `+0x30/+0x34`. Objects
occupy 8 bytes; root table type is `0x0a000020`. Two initialized spare slots
must exist before the marker is inserted. The callback's original root object
stays on the stack; only key/value temporaries are consumed. No VM pointer is
cached across reloads. The marker is an ASCII string `zh-CN:<dictionary SHA>`.

Runtime signatures exclude relocated absolute addresses in exception-handler
prologues. Full executable hashing, stable signature checks and dictionary
hashing must pass before any new hook becomes active. The native map starts
translating only after a VM marker was successfully published.

## UI and save boundary

The independent preload adds one query method to the main menu screen. The UI
reads the marker through the game's existing SQ bridge, accepting only its
own dictionary's token. The original connection handler and Script Hooks
handler both run. Unmarked sessions retain English geographic names.

The native map uses a rendering proxy with transparent glyph background. The
HTML adapter edits display text nodes and accessibility labels, leaving input
values, IDs, backend objects and saved names untouched. Existing saves that
already contain Chinese names are not migrated.

These checks are offline verification. Game startup, visual appearance and
third-party runtime integration still require in-game acceptance; the game
was not launched for this change, as requested by the user.
