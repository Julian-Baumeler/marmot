# Hardware / engine control

Valve and motor control for the Marmot test stand (MKS TinyBee / FluidNC).

| File | Role |
| --- | --- |
| [motor_config.yaml](motor_config.yaml) | FluidNC axis config (X = fuel, Y = O₂) for the TinyBee V1.0 |
| [valve_keyboard_controller.html](valve_keyboard_controller.html) | Browser overlay: keyboard → valve steps / ratio / home |
| [valve_area_calculator.py](valve_area_calculator.py) | Maps motor steps to circular-segment open area (%) |
| [Overview.drawio](Overview.drawio) | diagrams.net sketch of the setup |

## Quick start

```bash
# Opening-area table (0–200 steps)
python3 valve_area_calculator.py

# Keyboard controller: open the HTML file in a browser
# (talks to the FluidNC board on the local network)
```
