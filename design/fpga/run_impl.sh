#!/bin/bash
# Real implementation for the Tang Nano 9K (GW1NR-LV9QN88PC6/I5):
#   Yosys synth_gowin -> nextpnr-himbaechel (place & route, timing @ 27 MHz) -> gowin_pack (bitstream .fs)
# Open-source flow (Yosys / nextpnr / Project Apicula). Output: impl/visionaid.fs + reports.
set -e
cd "$(dirname "$0")"
EDA=../../tools/eda.sh
DB=/tmp/visionaid-eda-root/usr/share/nextpnr/himbaechel/gowin/chipdb-GW1N-9C.bin
mkdir -p impl
"$EDA" yosys -q -l impl/yosys.log -p "read_verilog rtl/va_common.v rtl/va_ultrasonic.v rtl/va_alerts.v rtl/va_pilink.v rtl/visionaid_top.v; synth_gowin -top visionaid_top -json impl/visionaid_synth.json"
"$EDA" nextpnr-himbaechel-gowin --chipdb "$DB" --device GW1NR-LV9QN88PC6/I5 --vopt family=GW1N-9C \
    --vopt cst=constraints/visionaid_tangnano9k.cst --json impl/visionaid_synth.json --write impl/visionaid_pnr.json \
    --freq 27 --report impl/nextpnr_report.json --placed-svg impl/placement.svg --seed 1 2>&1 | tee impl/nextpnr.log | tail -40
PYTHONPATH=/tmp/visionaid-eda-root/usr/lib/python3/dist-packages python3 -m apycula.gowin_pack -d GW1N-9C -o impl/visionaid.fs impl/visionaid_pnr.json
ls -la impl/visionaid.fs
