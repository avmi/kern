# Kern Sandbox: running a model's code from Python or Node

Your model writes the code. This runs it where it cannot reach your files unless you hand them over:
a real Linux container per call, and a hundred of them cost 1.4 s in total. What it CAN write is the
workspace you give it - a host directory, by default a temp one that is deleted when the session
ends - and `workspace_max_bytes` bounds that cooperatively rather than from the filesystem. How much survives between calls is
[your choice](#choose-how-much-survives-between-calls).

**Works with** Claude Code, Cursor, Claude Desktop, LM Studio, LangChain and pi.

`kern-sandbox` is the SDK in front of the `kern` binary: the isolation is the binary's, the package is
the API. On Linux `x86_64` and `aarch64` the package brings the binary with it, from PyPI and from npm
alike.

```sh
# if the venv line fails, your distribution ships it separately: sudo apt install python3-venv
python3 -m venv .venv && . .venv/bin/activate
pip install -U kern-sandbox
```

On a Mac, all of it goes inside a Linux VM: [macOS](INSTALL.md#macos).

```python
import kern_sandbox as kern

r = kern.run_code("print(sum(range(100)))")
print(r.stdout, r.fault)   # 4950  None
```

That call started a container from an OCI image, ran the code with **no network**, memory and PID caps
and a deadline applied from outside, then threw the container away. The next call gets a new one.

## When you would use this

**A script your model just wrote.** Paste it into `run_code` instead of your terminal. There is no
home directory of yours to delete and no key to read; a hallucinated `rm -rf ~` resolves to the
container's own read-only `/root`.

**An agent in a loop.** Give it the LangChain tool or the MCP server. Each step gets its own container,
so nothing step 3 left behind is waiting for step 12, and a step that hangs or runs out of memory comes
back as a value your loop can branch on.

**Analysis you did not write.** A chart comes back as an image the model can see, and a failure comes
back labelled, so you can tell a bug from the sandbox stopping it.

## The result says who stopped the run

`docker run` gives you exit 137 and leaves you to guess whether that was your timeout, the OOM killer
or something else. This tells you, as a typed field beside stdout and the exit code.

| the code | `fault.type` | `exit_code` |
|---|---|---|
| `print(sum(range(100)))` | `None` | 0 |
| `while True: pass`, `timeout_s=3` | `timeout` | 137 |
| `bytearray(400<<20)`, `memory_mb=128` | `oom` | 137 |
| `urlopen(...)`, network off | `None` | 1 |

The last row is the one a loop gets wrong: the network was off, so the **code** raised and the sandbox
did nothing. `fault` is read from a pipe kern writes, not from stdout, so code that prints `[exit 0]`
cannot fake it. The other values are `killed`, `workspace_full`, `escape_blocked`, `exec_failed` and
`startup_failed`. They and the exit codes are stable: one changes only to correct an outcome reported
wrong, and the release that does it says so first in its
[CHANGELOG](https://github.com/getkern/kern/blob/main/CHANGELOG.md) entry.

## Safe by default

A bare `Sandbox()` has no network, no host mounts, seccomp on, capabilities dropped and a **mandatory**
timeout. Every relaxation is a named argument.

**Two threats, and the second is not covered by the first.** A compromised dependency is stopped by the
filesystem and the network. A prompt-injected agent is not, because it runs the code you asked for. The
defence there is that the credentials were never in the box at all, which is why mounts over them are
refused rather than discouraged.

Two refusals have surprised people, both measured:

- **Mounts over sensitive sources are refused even if you ask**: the host's own directories, kern's own
  state, and 17 credential directories by name (`.ssh`, `.aws`, `.kube`, `.gnupg`, `.netrc`, `.npmrc`,
  `.git-credentials` and the rest), plus `~/.config/gh` and `~/.config/gcloud`. Mount a copy of what the
  code needs.
- **`network=True` includes the host's loopback**, where unauthenticated services live. A test read the
  host's SSH banner off `127.0.0.1:22`. [`egress_allow`](EGRESS.md) is the middle setting and is
  route-level, so a client that cannot speak to an HTTP proxy has no path out at all.

The caps bind only where your host delegates a cgroup. `kern doctor` says whether yours does, and
`require_limits=True` turns a silent no into a refusal to start. See
[Install](INSTALL.md#requirements-and-limitations).

**`user="node"` runs every box as that account of the image**, a name or a number; an image that
declares `USER` runs as it with no argument. The account maps to a uid of kern's range on disk, so
opening the sandbox starts one box to learn it and the workspace gets a POSIX ACL naming it. Everything
then works as usual, and what the account closes on purpose is read through a short-lived box running
as that same account. It needs a filesystem with ACLs, plus `setfacl` for Node, and costs about a
millisecond a call, measured.

## Choose how much survives between calls

Three levels, one argument apart.

| | per call | files carry | variables carry |
|---|---:|---|---|
| `kern.run_code(...)`, one-shot | 12.6 ms | no | no |
| a `Sandbox()` you keep open | 6.9 ms | **yes** | no |
| `s.kernel()` | 0.05 ms | **yes** | **yes** |

The first two give every call its own container and share the `/workspace` directory, so a file one
call writes the next one finds, while `x = 41` is gone with the process. `kernel()` is one long-lived
box with a warm interpreter: everything persists and the calls share one process.

```python
with kern.Sandbox(image="python:3.12-slim") as s:
    s.run_code("open('/workspace/f','w').write('ok')")   # a fresh container, file kept
    with s.kernel() as k:
        k.run_code("x = 41")
        k.run_code("print(x)")                           # 41
```

Measured with a
[precompiled image](https://github.com/getkern/kern/tree/main/examples/precompiled-image), 40 calls
each. On the stock `python:3.12-slim` the first two rows cost about three times as much and the third
does not change, because there the interpreter starts once.

**Pick the top row unless you need the others.** A hundred one-shot calls are a hundred containers and
**1.36 s in total** on the stock image, after which `kern ps -a` lists nothing. Move down the table
because you want the state, not because you are avoiding a cost.

`Sandbox(name="agent-1", persist=True)` keeps one box alive across calls and across processes, so a
second process naming the same sandbox finds what the first left in `/tmp`. It keeps the BOX, not the
interpreter: 11.4 ms a call against 13.9 for a fresh box, measured, while `kernel()` stays the fast
path. `/tmp` accumulates and the PID namespace is shared. It ends after `persist_ttl_s`, an hour by
default, or at `destroy()`. Node spells it `persist: true`.

## The one thing the host changes in your workspace

The workspace is yours and the host only reads it. There is one exception, and code inside the box can
trip it.

**A directory the box closes to the host gets its owner bits back.** The process holding your session
has to walk the workspace after every call: to tell you which files changed, to size it against
`workspace_max_bytes`, and to answer `list_files()` and `snapshot()`. So if `os.chmod("d", 0)` makes a
directory of yours unreadable, kern puts **read and search** back (`0o500`, never write) and says so in
a warning naming how many directories it touched. In short: **a mode-0 directory does not survive a
call.** It comes back at `0o500`.

**That does not buy you writing.** There is no write bit in `0o500`, on purpose, so a host-side
`write_file()` into a directory the box closed still refuses, naming the path. The alternative would be
the host silently re-opening a directory the workload shut.

Why repair rather than refuse: refusing is what it did before, and it was worse. The error came out of
the *reporting* path and took the result of the call with it, so one `chmod` ended the session. And
counting an unreadable directory as empty is how a size cap is defeated.

**If you need a directory the host cannot read, run the box as another account** (`user=` in the SDK,
`KERN_MCP_USER` for the MCP server). What that account creates is not the host's to change: kern leaves
it alone and asks a short-lived helper box, running as that account, to list and size it. A **file** at
mode 0 is left alone on every path, because a file's mode can be the data.

## Move a sandbox to another machine

Every box has a read-only root, so what a session builds up lives in its workspace: the files the code
wrote, and `.deps`, where `setup=` installs packages. `snapshot()` writes that workspace to one archive
and `restore()` puts it back, here or elsewhere:

```python
with kern.Sandbox(image="python:3.12-slim", setup="pip install orjson") as a:
    a.run_code("open('/workspace/state.json','w').write('{}')")
    a.snapshot("/tmp/ckpt.tar.gz")

# later, or elsewhere
with kern.Sandbox(image="python:3.12-slim") as b:
    b.restore("/tmp/ckpt.tar.gz")
```

It does not carry running processes, a `kernel()`'s variables, or the image, which the other host pulls
by name. An image that exists only locally travels with `kern save <image> -o image.tar` and
`kern load -i image.tar`.

The archive records the image and CPU its `.deps` were installed for, because a compiled package only
imports under the same Python, libc and CPU: `restore()` into a different image warns, and running
`setup=` again rebuilds them. A restored file keeps its **bytes, its modification time and its owner
permission bits**, so a tool that decides by timestamp sees the tree the snapshot captured. Group and
other bits are not carried: on a `user=` workspace those are the ACL's mask, and an ACL does not travel
in an archive. Symlinks, FIFOs and devices are not archived and `snapshot()` lists what it left out.
Both bindings read and write one format. In Node, `snapshot`/`restore` need
`KERN_SANDBOX_SNAPSHOT=1`.

A `kern box` started from the CLI, whose root is writable, moves at the image level instead:
`kern commit <box> <image>`, then `kern save` and `kern load`.

## From an MCP client

The package ships `kern-mcp`, a dependency-free stdio server: the model writes code, kern runs it on
your machine, and charts come back as images it can see. It works in any MCP client.

```json
{ "mcpServers": { "kern": { "command": "uvx", "args": ["--from", "kern-sandbox", "kern-mcp"] } } }
```

A client spawns the server from **its own** PATH, so a venv is invisible to it: `uvx` above installs
nothing, `pipx install kern-sandbox` is the other way. Per-client config, every `KERN_MCP_*` variable
and the remote form are in [the MCP page](MCP.md).

**The server is the middle row of the table above.** One session backs the whole connection, so a file
one tool call writes the next one finds, while each call is still a fresh box and variables are gone
with it. `KERN_MCP_KERNEL=1` makes it the bottom row, and the tool description tells the model which of
the two is in force.

## What it is not

This is a **kernel boundary**: namespaces, cgroups and seccomp, for your own or semi-trusted code. If
the code is actively hostile, or belongs to someone else, use a microVM (Firecracker, Kata) or gVisor.
That costs what a machine costs: about half a second per command there against about 14 ms here. The
full statement is the [threat model](THREAT_MODEL.md).

The binary comes with the Python package only on Linux `x86_64` and `aarch64`. Anywhere else, and for
Node, the package drives a `kern` on `PATH` or in `$KERN_BIN`.

## The rest

The full API, the LangChain tool and its shell policy, the benchmarks and the measured sharp edges live
with the package:
[bindings/python](https://github.com/getkern/kern/tree/main/bindings/python) on GitHub, and
[`kern-sandbox`](https://pypi.org/project/kern-sandbox/) on PyPI and
[npm](https://www.npmjs.com/package/kern-sandbox).
