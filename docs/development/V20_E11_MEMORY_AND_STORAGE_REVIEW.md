# LabMate v2.0 E11 software review

The app link allocates entry, UI and core code as separate sections. The E11 loader still enters through the original primary text section. The app-only build hook keeps the pinned Momentum base, SDK exports, app source features and approved renderer layout. In the local build the largest single allocation fell from 87,464 to 43,856 bytes. Aggregate preload remains about 117 KB, so this addresses contiguous allocation pressure.

The native review workflow validates the entry, section layout, executed relocation types, symbol targets and exact fast relocation parity against the ordinary ELF records. Malformed artifact tests exercise both table formats. The workflow saves the verified FAP and validation reports.

Profiles and preferences distinguish missing records from filesystem errors. A CSV create collision closes its attempted handle before the retry. The current software acceptance runner links the production storage adapters against a fault-injecting filesystem and exercises reopen, generation selection, fallback, writes, sync and cleanup. It also includes the History and OneWire regressions and current UI/core checks.

Use the linked native review workflow to build the sectioned E11 artifact. The older exact-local and USB scripts retain their historical artifact pins. Normal Momentum is a separate compatibility target.

Track device startup and storage evidence separately from source/build checks. Electrical validation belongs to the operator's later test pass.
