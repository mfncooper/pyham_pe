# Change Log

## [Unreleased]

## [1.1.2] - 2025-07-20

### Fixed

- Fixed missing TNC Port byte when sending raw AX.25 frame.

## [1.1.1] - 2025-05-26

### Fixed

- Fixed call from / call to order for incoming connections.

## [1.1.0] - 2024-10-17

### Added

- Add compatibility info for QtSoundModem.

### Changed

- Handle data associated with S frames. Some S frames (XID, TEST) have
  associated data, so split the text from the binary data. For now, we pass
  the text to the client; also passing the data will require an API change,
  which will happen in the next major release.

### Fixed

- Fixes for incoming connections.
- Fixed Documentation link on PyPI.

## [1.0.0] - 2024-04-03

- First public release.

[unreleased]: https://github.com/mfncooper/pyham_pe/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/mfncooper/pyham_pe/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/mfncooper/pyham_pe/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/mfncooper/pyham_pe/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/mfncooper/pyham_pe/tree/v1.0.0
