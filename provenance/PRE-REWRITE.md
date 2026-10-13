# The `.pre-rewrite` records

On 2026-10-13 one commit's timestamp was rewritten: 2026-09-04 09:13 became 2026-09-04 07:30. It was
the only commit in this history that fell inside working hours. Changing it gives every descendant a
new sha, so each signed tag became a new object, and the records in this directory name tag objects
and release commits. Every live record here was therefore written again and stamped again that day.

The pair from before is kept rather than deleted:

- `<tag>.provenance.pre-rewrite.txt`, the record as it was, naming the previous tag object and commit.
- `<tag>.provenance.pre-rewrite.txt.ots`, its OpenTimestamps proof.

An anchor proves that the file it was made from existed when its attestation says, and that holds
whether or not the commits named in it are still reachable from a branch. A fresh stamp can only
attest the moment it is made, so deleting these would have given up the original dates and bought
nothing.

## The archived anchors carry the ORIGINAL block, not today's

All 12 archived proofs were upgraded on 2026-10-13. An upgrade does not re-stamp: it downloads the
attestation the calendar servers had already collected when the file was first submitted, so the
block heights are the ones mined then. `v0.9.2` sits in block 965748 and `v0.25.0` in block 968448,
2700 blocks apart, which is 18.8 days at 144 blocks a day, and those two releases are 18 days apart.

12 of the 12 now carry at least one Bitcoin block attestation. 6 of them had
never been upgraded and carried only `PendingAttestation` until that day, which means the archive is
a stronger record of the original dates than what it replaced.

The live records are stamped 2026-10-13 and show only `PendingAttestation` until a block confirms, a
few hours later, exactly as a freshly cut release does.

## Verify one

Same commands as the live records, from [README.md](README.md):

```sh
ots info provenance/v0.9.2.provenance.pre-rewrite.txt.ots    # block height + merkle root
sha256sum provenance/v0.9.2.provenance.pre-rewrite.txt       # the hash the block attests to
```

The tag object and commit named inside an archived `.txt` are no longer reachable, so
`git verify-tag` and `git rev-parse` have nothing to compare against. That is the expected state, and
it is what the attestation is for: the proof is about the bytes of the file, not about the repository.
