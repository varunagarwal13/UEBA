# Contributing

## Branching
- `main` is protected — no direct pushes, all changes via pull request.
- One branch per engine: `feature/rules`, `feature/ecod`, `feature/hdbscan`,
  `feature/ctmc`, `feature/fusion`, `feature/profile`, `feature/ingest`.
- Keep branches short-lived. Open a PR as soon as something runs, even
  if `score()` still raises `NotImplementedError` for edge cases —
  small PRs are easier to review than one giant branch at the end.

## The interface contract
Every detection engine subclasses `DetectionEngine` from
`src/common/interfaces.py` and implements `fit()` + `score()`. Every
event is a `src.common.schema.Event`. Every engine returns a
`src.common.schema.EngineOutput`.

**Do not change `src/common/schema.py` or `interfaces.py` solo.** If
your engine needs something the schema doesn't support yet, raise it
with the team first — these two files are what let four people build
four engines in parallel without integration hell at the end.

## Ownership (fill in)
| Engine | Owner | Branch |
|---|---|---|
| Rules | | `feature/rules` |
| ECOD | | `feature/ecod` |
| HDBSCAN | | `feature/hdbscan` |
| CTMC | | `feature/ctmc` |
| Fusion | done (inverse-variance, see `src/fusion/fuse.py`) | `feature/fusion` |
| Profile layer | | `feature/profile` |

## PR checklist
- [ ] `python -m pytest tests/` passes locally
- [ ] New engine code only imports from `src.common`, never reaches
      into another engine's internals directly
- [ ] If you added a dependency, it's in `requirements.txt`

## Code style
`ruff` is installed in the devcontainer. Run `ruff check .` before
opening a PR. No strict style debates for the MVP — readability over
cleverness.
