# Huawei Solar — Companion Energy Integration Guide

This guide assumes the [wlcrs/huawei_solar](https://github.com/wlcrs/huawei_solar) integration is already installed and your **Huawei EMMA + LUNA2000 battery + SUN2000 inverter** are visible as devices in Home Assistant.

Get your customer and asset UUIDs from the Companion Energy dashboard under **Customer → Assets**. Find `BATTERY_DEVICE_ID` and `INVERTER_DEVICE_ID` under **Settings → Devices & Services → Huawei Solar → [device]** — the hex string in the browser URL bar.

---

## Step 1 — Push telemetry to Companion Energy

### Battery SOC every 5 minutes

```yaml
alias: "CE Telemetry — Battery SOC"
trigger:
  - platform: time_pattern
    minutes: "/5"
action:
  - service: companion_energy.submit_telemetry
    data_template:
      customer_id: "YOUR_CUSTOMER_UUID"
      asset_id: "YOUR_BATTERY_ASSET_UUID"
      soc: "{{ states('sensor.battery_state_of_capacity') | float / 100 }}"
```

### Inverter power every minute

```yaml
alias: "CE Telemetry — Inverter Power"
trigger:
  - platform: time_pattern
    minutes: "/1"
action:
  - service: companion_energy.submit_telemetry
    data_template:
      customer_id: "YOUR_CUSTOMER_UUID"
      asset_id: "YOUR_INVERTER_ASSET_UUID"
      power_kw: "{{ states('sensor.inverter_active_power') | float / -1000 }}"
```

### Grid connection — HomeWizard P1 meter every 5 minutes

The P1 meter exposes **cumulative** kWh totals, which map directly to `consumption_kwh` and `injection_kwh` in the telemetry service. Companion Energy tracks the deltas on its side.

```yaml
alias: "CE Telemetry — Grid (P1 meter)"
trigger:
  - platform: time_pattern
    minutes: "/5"
action:
  - service: companion_energy.submit_telemetry
    data_template:
      customer_id: "YOUR_CUSTOMER_UUID"
      asset_id: "YOUR_GRID_ASSET_UUID"
      consumption_kwh: "{{ states('sensor.p1_meter_total_energy_import_kwh') | float }}"
      injection_kwh: "{{ states('sensor.p1_meter_total_energy_export_kwh') | float }}"
```

> Check your exact entity IDs under **Settings → Devices & Services → HomeWizard Energy**. The sensor names vary slightly depending on your device name. For T1/T2 tariff meters, sum both tariffs: `{{ (states('sensor.p1_meter_total_energy_import_t1_kwh') | float) + (states('sensor.p1_meter_total_energy_import_t2_kwh') | float) }}`.

---

## Step 2 — Apply Companion Energy steering setpoints

Each asset type gets its own automation — CE issues setpoints per asset, so the battery and inverter steering state sensors are separate entities.

### Battery (LUNA2000)

Watches `sensor.my_battery_steering_state` and forces the LUNA2000 to charge or discharge at the power level Companion Energy specifies.

```yaml
alias: "Apply CE battery steering"
trigger:
  - platform: state
    entity_id: sensor.my_battery_steering_state
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.my_battery_steering_state
            state: "charge"
        sequence:
          - service: huawei_solar.forcible_charge_soc
            data:
              device_id: "BATTERY_DEVICE_ID"
              power: "{{ (states('sensor.my_battery_power') | float | abs * 1000) | int }}"
              target_soc: 95

      - conditions:
          - condition: state
            entity_id: sensor.my_battery_steering_state
            state: "discharge"
        sequence:
          - service: huawei_solar.forcible_discharge_soc
            data:
              device_id: "BATTERY_DEVICE_ID"
              power: "{{ (states('sensor.my_battery_power') | float | abs * 1000) | int }}"
              target_soc: 20

    default:
      # Handles: "self consumption", unsteered, and any other state
      - service: huawei_solar.stop_forcible_charge
        data:
          device_id: "BATTERY_DEVICE_ID"
```

### Inverter / solar panels (SUN2000)

Watches `sensor.my_inverter_steering_state` and limits grid export when Companion Energy requests curtailment.

```yaml
alias: "Apply CE inverter steering"
trigger:
  - platform: state
    entity_id: sensor.my_inverter_steering_state
action:
  - choose:
      - conditions:
          - condition: state
            entity_id: sensor.my_inverter_steering_state
            state: "curtailment"
        sequence:
          - service: huawei_solar.set_maximum_feed_grid_power
            data:
              device_id: "INVERTER_DEVICE_ID"
              power: "{{ (states('sensor.my_inverter_power') | float | abs * 1000) | int }}"

    default:
      # Handles: unsteered, max, and any other state — remove the export cap
      - service: huawei_solar.set_maximum_feed_grid_power
        data:
          device_id: "INVERTER_DEVICE_ID"
          power: 10000   # set to your inverter's rated power to remove the limit
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Entities show `unavailable` | Concurrent Modbus connection | Disable SDongle or FusionSolar local polling |
| Battery SOC missing | LUNA not detected | Check battery is wired to inverter and visible in FusionSolar |
| Connection drops periodically | Firmware bug or SDongle conflict | Update inverter firmware; remove SDongle |
| `installer` permission errors | Advanced features locked | Re-run integration setup with installer credentials (`00000a`) |
| Steering commands have no effect | Elevated permissions not granted | Enable "elevate permissions" during integration setup |

---

## References

- [wlcrs/huawei_solar — GitHub](https://github.com/wlcrs/huawei_solar)
- [Force charge/discharge battery — Wiki](https://github.com/wlcrs/huawei_solar/wiki/Force-charge-discharge-battery)
- [Changing Active Power Control — Wiki](https://github.com/wlcrs/huawei_solar/wiki/Changing-Active-Power-Control)
