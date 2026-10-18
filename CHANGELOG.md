# Changelog

**CLI stability.** Since v0.7.0 the verbs, their flags and the `--json` shapes change incompatibly
only on a minor bump, never on a patch, and only after a deprecation entry here one release earlier.
`--json` is additive, so consumers must ignore unknown fields. A `cli_surface_is_frozen` test fails
the build on any undocumented change. Full detail for any entry is in the git history.

**Sandbox result stability.** In kern-sandbox (Python, Node and `kern-mcp`), the `fault.type` and
`exit_code` an outcome reports change only to correct one that was reported wrong, and such a change
leads that release's entry, naming the outcomes it moves. kern-sandbox 0.2.45 is the example:
`os._exit(N)` in a prewarmed box or a kernel stopped reading as `killed`, and a kernel timeout went from
-1 to 137. New `fault.type` values are additive, so code must treat a value it does not know as a fault
of the sandbox. A test fails the build when the set of values changes in one binding and not the other.

**Compose surface stability.** A compose key kern reads keeps its meaning: it changes only to correct
a mapping that was wrong, and such a change leads that release's entry, naming the key. Reading a key
kern ignores today is additive. A key kern does not read is never silent, with two deliberate
exceptions: `x-*` extension fields, and the keys Docker itself does not act on under Linux
(`cpu_count`, `cpu_percent`, `cpus_shares`, `isolation`). A test carries the frozen list of keys and
both halves of that rule, so removing one from the parser fails the build by name.

## Unreleased

**A box could hand the host kernel checksum metadata of its own choosing, and two socket families
were reachable with nothing behind them.** `virtio_net_hdr` is how a sender supplies
`csum_start`/`csum_offset` instead of a finished checksum, and the parser behind it is what a VM
guest reaches through virtio-net. Measured in a default box before this: `CAP_NET_RAW` is effective
in the box's own user namespace, `socket(AF_PACKET, SOCK_RAW)` opens, and both options that enable
the header were ACCEPTED, while the invoking user cannot open a packet socket on the host at all.
The filter answers `setsockopt(SOL_PACKET, PACKET_VNET_HDR)` and `PACKET_VNET_HDR_SZ` with
`ENOPROTOOPT`, what a kernel without the option returns; both numbers, because 24 enables the header
as a side effect of setting its size. `socket(AF_XDP)` joins `AF_VSOCK` on the `socket` rule with
`EAFNOSUPPORT`: it carries the same shape of caller-supplied offsets and it OPENED in a default box.

Nothing a box uses is lost. `AF_PACKET` still opens, `PACKET_VERSION` and `PACKET_RX_RING` are still
accepted and a frame is still captured on `lo`, so `tcpdump` captures and `ping` pings;
`CAP_NET_RAW` is kept, as other runtimes keep it. This is not a fix for CVE-2026-99999 or any kernel
defect, and `docs/CVE-POSTURE.md` carries the counts behind that sentence, including the pair that
differs in one bit: a box with checksum offload on took 97,608 arrivals at the software-completion
predicate and entered it 0 times, and the same shape with the box turning offload off on its own
`eth0` took 42,721 and entered it 4,282.

## v0.33.0 - 2026-10-17

**`kern image inspect` emits the labels and the healthcheck it had already read.** Both are parsed
out of the image's own record and both were dropped before anything was printed: `Config.Labels`
appeared in neither rendering, and `Config.Healthcheck` appeared in the human one and not in the
JSON, so the two renderings of one image disagreed about what kern knows. An image's labels are
where `org.opencontainers.image.*` lives, so a consumer asking kern for an image's source, version
or licence was told it carries none.

**`kern compose exec` no longer builds.** It entered a box that is already running - it refuses with
"is not running" otherwise - and ran the file's whole `build:` section first, printing all of it, so
entering a running container cost a rebuild and buried the command's own output. It builds nothing
now, as `docker compose exec` does.

**`kern compose start` and `restart` stop printing `up`'s note.** Three verbs reach the line that
announces a stack returned instead of streaming, and all three were handed a sentence naming `up`,
pointing at a `-d` flag they cannot pass and claiming parity with `docker compose up`. The note
names the verb that ran, taken from the one table that defines them rather than a second list.

**`kern exec` works on hosts where it used to refuse outright.** With an allowlist of host shapes
that is not exotic at all - a shell in `/init.scope`, which is how WSL starts every terminal, and an
ordinary `ssh` session on Ubuntu 24.04, Fedora 44, Debian 13 and Rocky 10.2 - kern runs outside the
cgroup tree it delegates, and a process there cannot be moved into a box's cgroup: cgroup v2
delegation containment needs write access to the common ancestor, which is the root. `kern exec` and
`kern compose exec` therefore refused with 126, on hosts where the box itself was up and correctly
capped.

The scope carries no resource properties of its own and is named `kern-exec-<pid>.scope`, which is
deliberately not the `kern-box-` prefix that marks a cgroup kern may reap. Where no user manager
exists there is nobody to create a scope and the refusal stands, saying so; `KERN_NO_SCOPE` skips it
as it already does for `kern box` and `kern run`.

`kern doctor`'s scope-toll row said `kern exec` refuses on such a host. It no longer does, so the
row no longer says it.

**A build could reuse a layer that had been half-deleted, and say `built`.** `kern gc` reclaims
build layers no image references, and it did that with `remove_dir_all`, which stops at the first
directory it has no write permission on: a layer carrying a subuid-owned file, or any read-only
directory, was left on disk, uncounted and unnamed, while the pass could still take its `.ok`
sentinel. Where the sentinel survived instead, the build cache read a partially emptied directory as
a complete layer.

The sweep now removes the sentinel BEFORE it touches the directory, so any removal that cannot
finish leaves a layer with no sentinel, which is a cache MISS and costs a rebuild. It removes the
directory with the same forced, id-mapped remover `rmi` and `volume rm` already use, so a layer they
would have reclaimed is no longer left behind here.

**`gc` and the `kern top` Images tab say what they could not reclaim**, with the bytes still on disk
and the layer key, where a failed removal used to be dropped in silence. It is a note and not an
error: the sweep removed everything it could, and the exit code still reports that.

**A pull that could not be read reported a private repository.** `manifest_error` decided the cause
by looking for words anywhere in the response body, so an EMPTY body - what a dropped, timed-out or
proxy-filtered connection leaves - was reported as "cannot access '<repo>' ... it may be private
(run `kern login`)". Running the suite under load reproduced it against `library/alpine`, the most
public image there is.

**`kern exec` inside a user namespace no longer waits 25 seconds to fail.** The host-shape fix above
decided whether an exec can join a box's cgroup from `getuid()`, and a user namespace remaps ids
while leaving the cgroup alone: inside `unshare -Ur` the caller reads uid 0 over a path that still
says `user@1000.service`, so kern concluded it was outside a tree it was plainly inside and asked
for a transient scope from a manager with no `user@0.service` to put it in. A remapped uid is not a
different tree.

**`kern doctor` stopped contradicting itself in one sentence.** One row named the cgroup it had
probed and said "user manager delegates: none readable" about the same path, 10 out of 10 runs,
because the runtime and the doctor spelled the delegated root independently. There is one owner now.

**Nine documented claims said more than the code does, and a gate now refuses the second one.** The
README's lede, both package READMEs, `docs/MCP.md`, `docs/SANDBOX.md`, `docs/CVE-POSTURE.md`,
`docs/RESOURCES.md`, `docs/FAQ.md` and `SECURITY.md`'s in-scope list each promised something the
implementation does not keep - a sandbox that "cannot touch your machine" while the documented
`workspace=` is a host directory the box writes, an allowlist that is "always on" against the
`KERN_SECCOMP=denylist` opt-out, credentials that are "never in it" three lines above "only what you
pass with `env=`". `scripts/retired-claims.py` reads only the text a user meets and refuses an exact
string the code has moved past, each with the date it stopped being true.

## kern-sandbox 0.2.49 - 2026-10-17

**It carries the kern v0.33.0 binary.** Both bindings move together, as always.

**`workspace_max_bytes` is overshot by far less, and by an amount that depends on what the workspace
costs to MEASURE.** The in-call poller looked once a second whatever the limit was, so what got past it
was whatever the disk could write in that second: a 50 MiB cap stopped a box at 5,964,300,288 bytes,
113.8x the cap, and a report from a slower disk measured ~933 MB of the same thing. The interval is now
scaled to the remaining headroom, floored at 1 ms, and between two walks of the tree a cheap probe
re-checks the eight biggest files and every directory's fingerprint instead of walking it again.

⛔ IT IS NOT BOUNDED BY THE CAP, and an earlier draft of this entry said it was. Measured with the
headroom held at 50 MiB and only the pre-existing file count varied:

| files  | Python  | Node    |
|--------|---------|---------|
| 0      | 1.26x   | 1.30x   |
| 1,000  | 1.32x   | 1.80x   |
| 10,000 | 4.12x   | 8.40x   |
| 50,000 | 12.88x  | 12.80x  |

An interval can never be shorter than one walk of the tree, so on a large workspace the bound is the
walk's duration times the write rate, and Node pays more per walk (19.85 ms against 13.17 ms on the
same 10,000-file tree). The `workspace_full` fault says this and gives the figures. Closing it needs a
measurement that is not O(files), which would have to keep hard links counted once, symlinks refused
and a closed directory refusing the call, or it defeats the cap for good. The cap remains a measurement
and a kill on a host directory, not a refusal from the filesystem.

In Node the backoff that bounds the poller's own cost had never run: its timer was started after the
walk returned instead of before it, so it measured the comparison that follows and always came out at
zero. The sentence promising it was true in Python and false there.

**A file the box left at mode 0 is refused as a FILE, and as yours.** `read_file` answered "a directory
on that path is closed to this process and its owner bits could not be restored - it is not ours (a
`user=` session's box account owns it)" for a file owned by the caller's own uid: the subject, the
ownership and the `/proc` hint it ended with were all wrong, and the reader was sent to three dead ends.
`write_file` had the same defect and had not been reported. Both now name what they looked at - that it
is a file, its mode, its owner, and whether that owner is this process - and say that kern leaves a
mode-0 file exactly as the box wrote it because for a file the mode can be the data. A refusal that
really is a closed DIRECTORY is unchanged, and keeps `snapshot`'s wording, which was already right
because it enumerates the causes instead of asserting one; that sentence is now one spelling shared by
every surface that has to say it.

## kern-sandbox 0.2.48 - 2026-10-13

**It carries the kern v0.32.0 binary**, so `--egress-allow` on a sandbox refuses a plain-HTTP head
whose `Host:` names a host other than the vetted target. No binding code changed since 0.2.47.

The package descriptions did change, because two sentences in them were false: they said the
workspace cannot be bounded, which 0.2.47 had already stopped being true. They now say the cap is
measured while a call runs, and what it still is not.

## v0.32.0 - 2026-10-13

**A request `--egress-allow` used to forward is now refused, which is why this is a minor bump.**
With an allowlist in force, a plain-HTTP head whose `Host:` names a host other than the vetted
request-target, or that carries two of them, is answered 403. It was the way out of an allowlist
over port 80, and the check runs after the allowlist, so a refusal cannot probe it.

Over HTTPS the trick still works on a shared CDN, where that header is inside TLS; `docs/EGRESS.md`
says so. Nothing else in the binary changed since v0.31.0.

## kern-sandbox 0.2.47 - 2026-10-13

**A call that filled the workspace used to succeed anyway.** `workspace_max_bytes` was only checked
between calls, so a call that wrote past it returned normally, with the bytes on disk, and the
refusal arrived at the NEXT call. It now comes back with a new fault, `workspace_full`, and the box
is stopped mid-call.

This release carries the kern v0.31.0 binary, the same one the install line serves.

**The bindings**

- `workspace_max_bytes` is enforced WHILE a call runs, not only between calls. Measured before: one
  call wrote 8,115 MB in ten seconds against a 50 MiB cap and was admitted.
- New `fault.type` value `workspace_full`, additive. `KERN_MCP_WORKSPACE_MAX_MB` exposes the cap on
  the MCP server, where it was deliberately absent while the cap could only be checked between
  calls.
- One `chmod 0` from inside the box no longer ends the session. Code in a box could close a
  directory of its own workspace, and the host-side walk then raised a bare
  `PermissionError`/`EACCES` out of the reporting path: it destroyed the result of the call that had
  already run, and every later call failed the same way.
- Refusals name the mechanism where they used to print the kernel's errno: a symlinked directory in
  a READ or a listing (it said `[Errno 20] Not a directory`, while the write path already named it),
  a path component that is not a directory, and a directory that is readable but not writable.
- `snapshot()` and the workspace size measurement no longer raise a bare permission error when the
  repair cannot be made; both name what they could not read. The Node binding no longer counts a
  directory closed to it as zero bytes, which is how a cooperative cap is defeated for good.

**Documentation**

- `docs/MCP.md` documents that the workspace has no size bound by default, with the measured rate,
  the new cap, and a recipe a non-root user can apply (`$XDG_RUNTIME_DIR` is already a sized tmpfs;
  making a new sized mount needs root).
- `docs/SANDBOX.md` documents the one thing the host changes in a workspace, and what it does not
  buy.

## v0.31.0 - 2026-10-10

**`kern run --memory` REFUSES where it used to warn and run, and this one leads because it can stop
a command that worked yesterday.** The verb governs resources and nothing else, and it was accepting
a cap it could not apply: it printed "the command runs UNCAPPED" and executed the command anyway.

- A cgroup kern did not write counts as proof of a `--memory` only when its SWAP is bounded too.
- Caps now bind on a host whose `$XDG_RUNTIME_DIR/systemd/private` refuses connections while the
  user manager is alive.
- kern no longer calls a command UNCAPPED when the ceiling is proven.
- `kern exec -u <user>[:<group>]` runs the command as that account of the box, a name or a number,
  where `kern exec` could only be box root.
- `kern exec -u` no longer fails on the capability switch in a box started with `--cap-drop ALL`.
- `kern rm` no longer sends the reader to a listing that contradicts it.
- A detached box that cannot enforce its caps says so on the terminal, not only in its log.
- `kern inspect --json` no longer reports `"memory_max_enforced": null` for a box the kernel does
  cap.
- `kern images` says whether "no images cached yet" is the whole truth.
- A box no longer inherits the supplementary groups of whoever typed `kern box`.
- A workload whose image group list the box refuses (one gid outside the uid range) no longer keeps
  kern's own groups.
- kern-sandbox: `user=` (Node `user`, `kern-mcp` `KERN_MCP_USER`) runs every box as an account of
  the image, `persist` calls included.
- kern-sandbox: listing the workspace (`result.files`, `list_files`), `snapshot`, `restore` and the
  directories `write_file` creates now reach every path by descriptor, in both bindings.
- A compose stack joining an `external:` network no longer writes outside the other project's box.

36 further entries in this release are in `git log v0.30.2..v0.31.0`.

## kern-sandbox 0.2.45 - 2026-10-05

**Both packages carry kern v0.30.2**, so a `persist=True` call that `kern exec` refused (an ssh
session outside the delegated cgroup tree is the common case) is `startup_failed` with kern's own
message, where it read as the code's own exit 126 with no fault. With an older kern it still reads
as 126.

**Output printed before an OOM, a timeout or `os._exit` now reaches the caller on every path.**
0.2.43 made this true for a cold box only. The prewarmed box, which serves most `kern-mcp` calls,
and the resident kernel run a driver that sent a cell's output in the reply that ends the cell, and
a killed cell never sends one.

**One cell, one outcome, whichever box runs it.** On the prewarmed box and in the kernel,
`os._exit(N)` returns `exit_code=N` with no fault, where it returned `killed`. A kernel timeout
returns 137, where it returned -1: the timeout tears the kernel down, as it does a one-shot box.

**`kern-mcp` runs `ghcr.io/getkern/kern-sandbox:0.2.44` by default**, pinned by digest: python 3.12
with numpy, pandas and matplotlib, and node 22, for amd64 and arm64. A model that plots or asks for
`language="node"` no longer needs `KERN_MCP_SETUP` or another image, and the tool description says
what the image has.

**Opening a sandbox pulls a missing image first, on its own budget.** The first box used to pull it
inside its call's deadline: on a Jetson with an empty cache the first cell answered `startup_failed`
at the 30 s default. A pull that fails changes nothing, and the box reports it as before.

The `persist` docs said a call costs 2 ms; that was `kern exec` alone. A resident call still starts
a fresh `python3` and costs about what a fresh box does (11.4 against 13.9 ms on one host);
`sbx.kernel()` is the fast path.

## v0.30.2 - 2026-10-05

**`kern exec` no longer reports a command it refused as one that started.** When it cannot put the
command under the box's caps (a box at its `--pids-limit`, or a shell outside the cgroup tree kern
delegates, which an ordinary ssh session is) it refuses with exit 126, and it also wrote the
"started" bytes on `KERN_STARTED_FD`, so an SDK read the refusal as the code's own exit 126. It
writes nothing now, as `kern box` does for a box that never started.

- An image `kern save` or `kern push` wrote can be the base of a `podman build`: the config carries
  the `history` entry buildah requires for each layer.
- `kern box --help` says `--user` also takes a name from the image's `/etc/passwd`, which it always
  did.

## kern-sandbox 0.2.44 - 2026-10-04

**Both packages carry kern v0.30.1**, so a resident sandbox (`persist=True`, Node `persist: true`)
reports an OOM as `oom` where it reported `killed`, and a cell's own `exit(137)` as an exit with no
fault where it reported an external kill. Measured in both bindings; with an older kern on `PATH`
both still read `killed`.

## v0.30.1 - 2026-10-04

**A compose `devices:` entry needs `--allow-device-grants`, as the pages already said.** kern 0.30.0
gave a box `/dev/kvm` or a GPU's modeset node from a compose file run with no flag. Such a file now
stops with a message naming the service and every node; pass `--allow-device-grants` to run it.

**`kern save` and `kern push` work on Debian- and Ubuntu-based images on a host with a subuid
range.** Both failed there, on `python:3.12-slim` and on anything built on it, because the image's
`/var/cache/apt/archives/partial` belongs to a subordinate uid; Alpine was unaffected. `kern gc`
also removes the copies `--pull always` retires, which it left behind on the same hosts.

**`kern exec` tells an SDK how the command ended.** A resident sandbox (`persist=True`) now returns
`fault.type == "oom"` for an OOM where it returned `killed`, and a cell's own `exit(137)` reads as
an exit instead of an external kill.

**A `-v` aimed under `/sys/devices` reaches the box.** The CPU topology kern writes there covered
it.

**A base image without `/bin/true` builds layered**, instead of building flat and blaming the kernel
("unprivileged overlay unavailable").

**`kern inspect` answers for a built image.** It said "nothing named" for every image `kern build`
made, while `kern images` listed it.

**Three messages name the right thing:** compose `gpus:` is described as Docker's GPU request rather
than a typo for `cpus:`; `kern pull` names `kern box … --pull always` to refresh an image; and a
failure reading a cached image no longer says to check the image's name.

## kern-sandbox 0.2.43 - 2026-10-04

**`npm install kern-sandbox` brings kern with it, and both packages carry kern v0.30.0.** On Linux
x64 and arm64 the npm package carries kern's static release binary, the same file `install.sh`
serves, and the Node binding takes it after `$KERN_BIN` and before `PATH`, as the Python wheels do.
Python and Node are at one version again.

**A one-shot cell no longer inherits the caller's stdin.** Under `kern-mcp` that descriptor is the
JSON-RPC transport, so a cell could read bytes meant for another tool call. `input()` now gets EOF.

**A warm or resident box built under another posture is no longer handed over.** The prewarm pool's
key and the `persist` fingerprint now come from one function: the argv, every `KERN_*` variable kern
reads when it builds a box, and what a `vcpu:`/`vgpio:`/`vdisk:` profile resolves to. A changed
`kern.toml` definition or `KERN_SECCOMP` used to leave the key unchanged.

**The wheel's kern is identified by the hash its RECORD lists, not by the path.** `pip install
--target DIR` writes a RECORD entry that points two levels above `DIR`, and a kern there was taken
over the wheel's own. Now a candidate is taken only when its bytes match, and `DIR/bin/kern` is
found.

- **`persist=True`** (Node: `persist: true`) keeps one resident box per `name` and runs every call
  in it with `kern exec`: 2 ms a call against 6 ms for a fresh box, and another process adopts it.
  It needs `name` and an explicit `workspace`.
- **`workspace_max_bytes`** (Node: `workspaceMaxBytes`) caps what a workspace accumulates across
  calls. It is cooperative: the call that exceeds it runs, and the next is refused.
- Output survives an OOM or a timeout: the interpreter runs unbuffered.
- `os._exit(0)` under a memory cap is reported as a clean exit, not as an external kill.
- `language="node"` is refused on the default image, which has no node, and the refusal names the
  remedy.
- The MCP server caps each stream at its reply budget. A cell printing 100 MB used to cost 129 MiB
  of server memory to show 16k characters; it now costs 3 MiB.
- The MCP server answers `-32700` for every id on a line that is not one message (two frames, a
  frame cut short), and refuses `NaN` and `Infinity`.
- `index.d.ts` declares the eight constructor options it lacked, among them `persist` and
  `requireLimits`, plus `destroy()`. It also stops saying `depsReadonly` defaults to false: the
  default is true.

## v0.30.0 - 2026-10-04

**kern says when a limit above a box will stall it instead of letting it be killed.** Past a
`memory.high` on a cgroup above the box the kernel throttles allocations rather than OOM-killing, so
a box that should die at its cap hangs until its timeout: with `MemoryHigh=80M` on `kern.slice`, an
OOM that takes 0.06 s took 317 s. kern now prints a `kern: note:` naming the cgroup and the command
that lifts it, `kern doctor` and `kern inspect` report it (`memory_high_outer` and
`memory_high_outer_cgroup` in `--json`), and `--require-limits` refuses to start such a box.

**`kern box --show-config` prints what a profile grants, not only its cgroup numbers.** Three lines
follow `privileged:`: `devices:`, `sysfs:` and `vdisks:`, each sorted, `-` when empty. Two different
device grants under one profile name used to print identical output.

**On Windows, `kern.exe` says which WSL2 distro it runs in and lets you choose:** `kern wsl list
[--probe] | status | use <distro> | reset`. `use` warns when `KERN_WSL_DISTRO` is set, because that
variable wins over the stored choice.

**`kern compose restart` no longer hangs on a one-shot dependency that already completed.** It
waited 120 s, exited 1 and left the service down; `service_healthy` dependencies waited the same
way.

**`kern doctor` no longer says "ready" on a host where a box dies at the `/proc` mount**, and it
reports when more than one kern is installed and the versions disagree.

**The note about two services on one internal port names both services and the port**, and `ps`,
`restart` and `logs` no longer print it.

**`kern build --check` names a `COPY --from=` stage it cannot resolve** instead of saying the file
builds here.

**`install.ps1` no longer leaves `$ErrorActionPreference = 'Stop'` in the PowerShell session it was
piped into**, where every later command writing to stderr became a terminating error.

The sandbox SDK and MCP server changes on this line (resident named sandboxes, a workspace cap, an
MCP server that answers every request id it can read) ship as kern-sandbox, with Linux wheels that
carry this kern.

## kern-sandbox 0.2.42 (Python) - 2026-09-29

**The Linux wheels carry kern v0.25.1**, so `pip install kern-sandbox` brings the pull that ends a
stalled image download after 30 s and retries it, instead of waiting ten minutes.

## kern-sandbox 0.2.41 (Python) - 2026-09-29

**`pip install kern-sandbox` is the whole install on Linux.** The wheels for `x86_64` and `aarch64`
carry kern's static release binary, v0.25.0, the same file `install.sh` serves and checked against
its published sha256. pip installs it as `kern` next to `python`, the way ruff and uv ship theirs,
so the venv has `kern doctor` too.

**The SDK takes the kern its own wheel installed, and finds it through the package's RECORD.** The
order is `$KERN_BIN`, then that binary, then PATH.

**On a Mac, the error and the pages say where the code goes**: inside the Linux VM, where the same
`pip install` brings kern.

## kern-sandbox 0.2.40 - 2026-09-26

**The page says what it works with, by name.** Claude Code, Cursor, Claude Desktop and LM Studio,
instead of "MCP clients", which a reader has to already know they are one of.

**Credentials get their own paragraph, because filesystem and network do not cover them.** A
compromised dependency is stopped by the box; a prompt-injected agent is not, because it runs the
code you asked for.

**The tool-call chart is in multiples of one call, not milliseconds**, and carries the range in its
own footer: `print(1)` is the workload that flatters it most and a heavier call is 7x rather than
20x.

**The Node page had the opening the Python page replaced in September** and never got the same fix:
the rejected title, and a note about measurement method above the first example.

## v0.25.1 - 2026-09-29

**Two threads asking whether memory caps work could get two different answers.** The probe named its
throwaway cgroup once per process, so a second thread removed the first one's directory to retry,
and the first then probed a directory that was no longer its own.

**A registry transfer that stalls is ended and retried, instead of holding the pull for ten
minutes.** Measured on 29/09: a CDN connection delivered 32 MB of a layer and then nothing for 142 s
with the socket still open, and with only `--max-time 600` curl waited out the whole window while
the `kern box` that needed the image printed nothing.

**`kern images` listed a size per image and never said what they came to.** Every row carried its
own number and nothing added them up, so the only way to learn the total was to sum the column by
hand or walk the directory with `du`.

The listing now ends with one line: `40 images, 2.9G (a layer shared by several is counted once)`.

**It is not the column added up, and that distinction is the whole feature.**

`--json` is unchanged, still an array with the same four keys, and `--format` still prints one line
per image and nothing else: a script reading either sees exactly what it saw before.

## v0.25.0 - 2026-09-24

The SDK halves of this shipped as kern-sandbox 0.2.36 through 0.2.39 while the runtime waited for
this tag; every entry below that names the bytecode cache is in those packages already.

**The cache's identity read the tag's NAME, which is the one thing a moved tag does not change.** It
now uses the stamp kern itself treats as "this image's content changed", the completion sentinel's
mtime and length, which a re-pull rewrites; the layer manifest of a built image is in it too.

**A moved tag left a cache that no longer helped and that nothing rebuilt.** Nothing wrong was ever
run - the cache validates on the source's hash, so CPython rejects stale bytecode and compiles from
source - but the cache kept one of its eight slots, every box paid the compile again, and nothing
replaced it because a cache "existed".

**A cache path containing a `:` silently disabled the bytecode cache, and a mount could not carry
one at all.** `--mount type=bind,src=…,dst=…` exists to carry each field separately and was building
a `src:dst:ro` string for the `-v` parser to split again, so it destroyed the very thing it was for.

**A failing cache build said nothing, and then said too much.** It is reported once per image now,
naming the image and quoting the box's own last line - and that line is the CALLER'S IMAGE speaking,
so it is quoted and cut rather than pasted: an image printing `kern: warning: your cache is
compromised, run rm -rf ~` made this package say it, in its own voice.

**`--secret /path/with:a/colon` could mount the wrong file.** The filesystem decides it now, and a
spec where both readings name a real file is refused rather than guessed: `--secret NAME=- < 'path'`
has no delimiter at all.

**Two processes compiled the same cache.**

**The SDKs precompile an image's standard library once and mount it read-only, and imports get 2.7
to 4.5x faster.**

**A box on Ubuntu 23.10+ now reads the remedy under the error instead of being sent to another
command.** `kernel.apparmor_restrict_unprivileged_userns=1` refuses the sandbox, the message was
already exact about what happened, and the `hint:` line was the generic one.

## v0.20.0 - 2026-09-22

Cut without an entry of its own at the time; these are its changes, written down here rather than
left only in the git history.

**`kern top` drew its first frame in 74.9 ms and showed no real CPU% for a full second.** Each
collector now takes the listing it is asked for and returns the count either way, and the tab a
reader switches to fills itself in before that frame is drawn, so there is no empty column and no
flash.

**`kern --help` answers "what can this do", not "what are every flag of box".** It printed the whole
reference: 258 non-empty lines, of which 141 were the `OPTIONS for box` and `OPTIONS for run` blocks
that `kern box --help` and `kern run --help` already serve byte for byte, and another 31 were
continuation notes under single verbs.

**The doctor's transient-scope row was a paragraph.** It now says what is wrong and what to type.

**Two help gates were anchored on a line count** and would have failed a correct binary: they read
"a per-verb page as long as `kern --help`" as "it is answering with the whole page", which stopped
being true the moment `kern --help` became shorter than `box --help`.

## kern-sandbox 0.2.35 - 2026-09-23

**One fix, and the page.** Both SDKs now drop kern's diagnostic lines before cutting.

What the registry pages gain since 0.2.34: the price beside "one container per call" (a hundred
calls, 1.4 s, nothing left behind), which persistence level the MCP server gives, a corrected `rm
-rf ~` claim (the root is read-only, so the delete fails), a seven-call demo, the fault table at six
rows, and the line saying it does not run inside a container without `--privileged`.

**The package description leads with the slogan** instead of "one per call", and keeps the sentence
conceding that a kernel boundary is not a microVM.

## kern-sandbox 0.2.34 - 2026-09-22

**Documentation only, and published for the same reason 0.2.33 was: a registry page is an imprint of
the moment it was published.**

What the registry pages gain: the slogan, the animated demo of the three verdicts, the table
comparing this to a venv, docker per call, bubblewrap, a microVM and the cloud services, and a
current-limitations section that leads with what this is not a boundary against.

**The package description is 198 characters instead of 343.**

## kern-sandbox 0.2.33 - 2026-09-22

**Documentation only: no code changed between 0.2.32 and this.** Republishing is the only way to
move that imprint.

## kern-sandbox 0.2.32 - 2026-09-21

The bindings are released on their own clock, so this section carries a package version rather than
a runtime tag.

**The MCP server starved its own setup box.** Unset now reaches the SDK as `tmpfs=None`: cells still
get 64 MiB, an explicit value still applies to every box, `0` still means none.

## v0.10.0 - 2026-09-21

Four days of work since v0.9.35, and 99 commits.

**Read these first if you are upgrading.** **A pod maps the sub-uid range by default**, as an
`--image` box already did, so a member running an image that drops privilege in its entrypoint works
without `--uid-range`; `--no-uid-range` is the opt-out.

### Flags and verbs, accepted where kern has the same knob

`box --mount` and `--name`, `--rm`, `network inspect`, the `image` verb group, `images <repo>` with
`--format` and `pull --quiet`, `inspect --format` answering `{{json .NetworkSettings.Ports}}` and
`{{json .Config.Labels}}`, `kern port`, `logs --since/--until`, `ps --filter health=`, `--no-trunc`,
`images --filter`, `stats --no-stream`, and `build` reading a `Containerfile` so a project need not
carry another project's name.

Six of the twelve commits that built this surface are FIXES those passes found in it, and one was
live on 0.9.35: **`--mount readonly=1` mounted the path WRITABLE**, which is the worst shape a
compatibility gap can take, the flag asking for less privilege granting more.

### Compose

`compose push` exited 0 having published nothing, and would have published images the file did not
build.

### The SDK

**kern-sandbox 0.2.31.** The constructor guards that existed for `setup` and `cap_drop` and not for
the rest: `mounts` and `env` in the wrong shape name the argument and the shape they want, instead
of escaping as an `AttributeError` in Python or reaching the mount validator as an index key in
Node, where `Object.entries` does not throw on an array and reported a source of `"0"` the caller
never wrote.

The mount guard refused AWS and Azure and accepted Google Cloud, which is the asymmetry that made it
visible.

0.2.30 was published with `package.json` raised and the version constant in `index.js` left behind,
so the package reported the previous release; 0.2.31 corrects it.

### Boxes, pods and lifecycle

**Stopping a pod's last member removed the pod, and letting that member exit on its own did not** A
pod created by name now survives being emptied; `stop --all`, naming the pod itself, and a pod
derived from a stack still tear one down.

**Every box leaked its environment sidecar.** kern records a box's environment so `kern exec` and
the healthcheck can read what `/proc/<pid1>/environ` stops giving them once the box drops privilege,
and only `stop` ever removed it: a box that simply EXITED left it behind forever, which is every
foreground box and every SDK call.

`kern wait` was diagnosing a cause it could not know.

### What the output says

**A cell could forge a sandbox verdict with one leading space** `kern network ls` and `kern pod ls`
printed a name off disk without stripping terminal escapes; `inspect --format` printed a label's
control bytes raw where `ps --format` strips them.

### Performance

**A box that drops every capability stops paying for a uid range it cannot use: 937 us** , a quarter
of a cold `--image` box, measured paired at n=300 with an interval of [-959, -912].

The CPU topology a box sees was built in its overlay upper and paid for twice; that same loop re-
resolved a ten-deep path once per CPU.

### Measurement and the pages

The README publishes **no latency figure** at all: a front page states a number with no machine,
method or date beside it, and it is the one claim there nobody can check without running something.

`kern doctor` is now the first command after install, on Linux and inside the macOS VM.

The timing instrument could not state its own coverage, so a reader summed its phases and believed
the sum was the box; it now closes with the total from process entry, what the marks cover, and the
remainder as a number.

## v0.9.35 - 2026-09-17

Eight days of work since v0.9.32.

**Read these first if you are upgrading:** each compose service gets its own network namespace on a
bridge, so a port a service binds on its `127.0.0.1` stays private to it; `fault.type` reports a
different value for four events; and the SDKs refuse mounts they used to accept, with no opt-out.

**Sentry's official `install.sh` completes on kern, and the 57-service stack runs.**

**Each service gets its OWN network namespace on a bridge, which is Docker's arrangement.** `--pod`
keeps the old single shared namespace, which is faster and makes every loopback port reachable by
every peer, and `kern compose <file> config` prints which wiring a bring-up will use.

**Two networking defects that only some machines could see.** On a home or edge network a box had
internet and could not resolve a name, because pasta copies the host's nameserver into the box and
on such a network that address is the LAN router, which is also the gateway pasta impersonates; kern
passes `--dns-forward` now.

**`compose run` was missing most of what a script passes it.** `-d` detached nothing; `--name`,
`--entrypoint`, `-e`, `--user` and `--pull` were refused; the one-off started none of the
dependencies written with a `condition:`, which is how every real file writes them, and did not wait
for them.

**A service whose dependency failed was held back and then started anyway.** With a `condition:` on
a dependency that fails, the pre-exec gate refused the exec, and one second later the restart path,
running without that gate, ran the workload.

The stream is neutralised per LINE rather than per chunk.

17 further entries in this release are in `git log v0.9.32..v0.9.35`.

## v0.9.32 - 2026-09-09

**A published port now binds `0.0.0.0`, not `127.0.0.1`.

**Docker Compose compatibility went from 14% to 94%** [Corrected under Unreleased: 94% is the
ceiling, and this definition measures 35% on the same corpus.] What remains is dominated by keys
asking kern to be less confining than it is (`privileged: true`, `security_opt`) and by
`network_mode: host`, which one namespace per stack cannot express.

**Twelve compose keys stopped being warnings and became behaviour** A string `command:` is now an
argv rather than a shell line, a tagged block scalar folds, and an empty named volume is seeded from
the image as Docker does.

**`networks:` is a boundary, not a warning.** Under `--no-pod`, services with no network in common
cannot reach each other by name or by address, and `internal: true` is the absence of NAT rather
than a filter, so a published port does not open a way out.

**`${VAR:?message}` refuses the file instead of substituting an empty string.**

**An image's file ownership survives the unpack** A named volume inherits the image directory's
owner and mode, not only its contents, and `kern rmi` no longer reports a removal it did not
perform.

```
                  median     p99      max
before             4.700    5.735   15.304 ms
after              0.870    1.267    1.487
```
The tail moved more than the median because a D-Bus round trip to a shared user manager is a queue.

6 further entries in this release are in `git log v0.9.31..v0.9.32`.

## v0.9.31 - 2026-09-09

**If you use `kern exec`, this release is the one that makes it obey the box's limits.** A command
run through `kern exec` was placed in the CALLER's cgroup, outside the box's `--memory` and `--pids-
limit`, and said nothing about it.

```
box PID 1                  .../kern.slice/kern-box-<tag>-<pid>     capped
the kern exec'd process    .../app.slice/app-<the caller>.scope    the CALLER's cgroup
```
A fork bomb or a memory hog started with `kern exec` therefore ran without the ceiling the box was
given.

**The cost is real and is stated rather than hidden.**

**A command killed by the box's memory cap now says so.** `memory.oom.group` kills the whole box,
the exec'd command included, and it goes by SIGKILL, so the process that would explain it is the one
being killed.

**A box whose registry record is lost stays visible.**

**Multi-stage builds produce an image that runs.** The final image is now materialized, fail-closed.

**Compose reads files it used to refuse, and refuses files it used to accept in silence.** A
`command:` continuation line starting with `-` was read as a sequence entry, so `--source`, `-drive`
and `-netdev` broke a plain folded scalar; two real files from public repositories now parse.

**`kern build prune` refuses arguments it used to ignore.**

**Known and unchanged:** CI does not start boxes, and the second test's host has no cgroup
delegation, so `--memory`/`--pids-limit` enforcement has one witness.

## v0.9.3 - 2026-09-07

**If you run kern on Ubuntu 23.10 or later, your install needs one action.** That is not a new
feature, it is the answer to "why does no box start", and it is here rather than under new
capabilities because it is the entry a reader scanning for "does this release affect me" needs to
find.

```
kern doctor --apparmor-profile | sudo tee /etc/apparmor.d/kern >/dev/null
sudo apparmor_parser -r /etc/apparmor.d/kern
kern doctor
```
**CLI, additive:** `kern doctor --apparmor-profile` writes that profile to stdout and exits without
running any check.

**What that file does NOT do** Removing it returns the machine to its previous state.

The third command is not politeness.

`kern doctor` prints that install line, names the path it is running from because AppArmor attaches
by path, and offers `sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` only after it, with
its cost: that one lifts the restriction for every program on the machine and is lost at reboot.

**`kern doctor` said "ready" on a stock Ubuntu 24.04, where no box can start.** Ubuntu 23.10 and
later ship `kernel.apparmor_restrict_unprivileged_userns=1`, which PERMITS the namespace and refuses
the rootless uid map, so the probe succeeded on a host where the very command doctor then suggested,
`kern box hello`, failed.

The probe now runs the sequence a box actually runs, in the same order: unshare, deny setgroups,
write the uid map.

```
default                       ✘ the namespace is allowed and its uid map is REFUSED - no box can start
                              not ready - 1 blocker(s)
apparmor_restrict...userns=0  ✔ enabled
                              ready - `kern box` will run here
```
The AppArmor line no longer hedges with "if boxes fail with EPERM".

**On a host whose SELinux policy refuses pasta's netns watch, the pod's pasta no longer exits by
itself.** kern retries with `--no-netns-quit` there
([#6](https://github.com/getkern/kern/issues/6)), and a pasta started without the watch does not
notice the namespace disappear, so `kern pod rm` and `compose down` are what stop it rather than
pasta stopping itself.

**`stdin_open:` and `tty:` in a docker-compose.yml no longer produce an alarm.**

**The Rust test suite had never been built for aarch64, though the binary always was.** It now
builds and runs on ARM: **577/577 on a Raspberry Pi 5 (kernel 6.6) and on a Jetson (5.15-tegra)**,
on the hardware rather than under emulation.

That is the largest instrument defect in this cycle: not a probe reading the wrong thing, but a
whole suite that was never executed on a target kern ships for.

| passt | ships in | on a refused watch |
|---|---|---|
| `0.0~git20230309` | Debian 12 | `inotify_init(): won't quit once netns is gone`, and it keeps the NAT |
| `0.0~git20240220` | Ubuntu 24.04 | `netns dir open: %s, exiting` |
| `0^20250919` | Fedora 43 | `netns dir open: %s, exiting` |
So a Raspberry Pi on Debian 12 needs no retry and never could have: issue #6 cannot occur against
the tolerant build.

The same mistake had a second instance, found by adding one diagnostic line to the reproduction
script rather than by reading the code.

The enforcement byte on `KERN_STARTED_FD` was already correct: it takes the box's directory
explicitly, for this exact reason.

```
error: sandbox: fork(idmap helper) failed: Resource temporarily unavailable (os error 11)
hint: needs unprivileged user namespaces and a valid --rootfs directory
```
The message is exact and the hint names two things that are both already fine, because the code
could not have reached that fork otherwise.

The version is still the tag and nothing is carved into the source.

4 further entries in this release are in `git log v0.9.2..v0.9.3`.

## v0.9.2 - 2026-09-06

**Cut for a defect the first person to try compose would hit.**

It does not present as a missing network, which is why it survived: the image ships its own
`resolv.conf` and it looks healthy, so the failure surfaces as `Could not resolve host` and every
diagnosis goes after DNS.

**Every compose test in this repo ran three services, which is how it shipped.**
`scripts/acceptance-matrix.sh` now has a case for it, with its two new assertions exercised in
`--self-check` including a negative control on the pre-fix summary line.

## v0.9.1 - 2026-09-05

**Faster than v0.9.0 on a bare box start** The supervisor's sibling cgroup is created only where it
is needed, a scope or managed unit whose own cgroup is the one armed with `oom.group`: 0.165 ms
back, 24 of 24, re-checked in both layouts on four hosts and four systemd versions (249, 252, 255,
257).

**Cut for one defect the released binary had on most hosts.** `--egress-allow` in v0.9.0 could start
a box against a proxy nothing could reach, and on three of five hosts the pump never got the port
(`cannot bind 127.0.0.1:3128 in box: Address not available`).
