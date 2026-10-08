# Cross-check: same RTL, out-of-context synthesis + implementation on Xilinx Zynq-7020 (PYNQ-Z2 class)
# at the 27 MHz board clock. Run: vivado -mode batch -source vivado/vivado_crosscheck.tcl
set here [file dirname [file normalize [info script]]]
set rtl  [file join $here .. rtl]
read_verilog [glob [file join $rtl *.v]]
synth_design -top visionaid_top -part xc7z020clg400-1 -mode out_of_context
create_clock -name clk -period 37.037 [get_ports clk]
opt_design
place_design
route_design
report_utilization    -file [file join $here utilization_xc7z020.rpt]
report_timing_summary -file [file join $here timing_xc7z020.rpt]
