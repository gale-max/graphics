# Dual Backend Source Checkpoint

These commits record the glibc/toolchain migration and selectable NanoPC-T4
RT and ThreadX backends on master. They are local commits; no remote push is
claimed. The graphics repository commit containing this file records the
build-entry changes and [board evidence](GLIBC_RT_MIGRATION_20261020.md).

| Repository | Commit |
| --- | --- |
| `components/arch-armv8a` | `bd067c23226a84df42979d2ce80f1e3295a7235f` |
| `components/linux-runtime` | `7fa04deb85bfe137f86aeae0e57c54cae4c17514` |
| `components/loader` | `43c8112d3e85a241a7212e21c400d7e7913888c7` |
| `components/ulib` | `32d49e67a7846c72d51e0a5fdf08b961ffd581fb` |
| `luna` | `034fdaaa9da2243ebda836859d5ceb59bc6854fb` |
| `luna-test` | `77d32d653533e1842ac2be96016d0b4cec4c7334` |
| `rockchip` | `9aa44005bf1fd872c5829e60f5131be329522875` |
| `rt-smp-nano` | `d438ab1a784e7a8678df54b03fbd9eb0f2c042ad` |
| `threadx` | `bcf3ff0623b484456b0ba66354dd46ab1c283bf6` |
| `virt` | `3efc2aa079d08a35bb2ddc9ec0301572de60602c` |
| `zynq7k` | `313b3ffe2ffc3b29e3a3ccfe61c4fd94ee58201d` |
| `integrated` | `f958d6d545a24329826caad7c2c61d80c29df737` |
| `components` | `efab99ce9e2e422e947833601d59dd67e1e7af95` |

RT thread-name termination changes passed host tests after the accepted RT
BIN was produced; they are not included in that board-tested BIN. The local
six-core default-header drift is not part of the luna commit; NanoPC uses
explicit target CPU settings. Use the image hashes in the evidence document
for runtime attribution rather than assuming a rebuilt image is identical.
