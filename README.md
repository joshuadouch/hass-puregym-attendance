# PureGym Attendance for Home Assistant

A Home Assistant integration that shows how many people are in your PureGym home gym right now, the same number the PureGym app shows.

It logs in to the PureGym members' app API with your app email and PIN, finds your home gym, and polls its live attendance (every 5 minutes by default).

> Unofficial. PureGym doesn't publish this API and may change it at any time.

## Sensors

All sensors sit on one device named after your gym (for example **PureGym Andover**).

| Sensor | What it shows |
| --- | --- |
| People in gym | People in the gym now. Attribute `capped` is true when PureGym shows a capped count such as "100+". |
| People in classes | People booked into classes running now. |
| Capacity used | People as a percentage of the gym's capacity (only when PureGym gives a capacity). |
| Maximum capacity | The gym's capacity (diagnostic, off by default). |
| Last refreshed | When PureGym last updated the count (diagnostic). |

## Install

### HACS

1. In HACS, open the menu ⋮ → **Custom repositories**.
2. Add `https://github.com/joshuadouch/hass-puregym-attendance` with type **Integration**.
3. Install **PureGym Attendance** and restart Home Assistant.

### Manual

Copy `custom_components/puregym_attendance` into your Home Assistant `config/custom_components/` folder and restart.

## Set up

**Settings → Devices & services → Add integration → PureGym Attendance**, then enter the email and PIN you use in the PureGym app.

To change how often it checks, open the integration and choose **Configure**. If you change your PIN, Home Assistant will ask you to log in again.

## Example: notify when the gym is quiet

```yaml
automation:
  - alias: Gym is quiet
    trigger:
      - platform: numeric_state
        entity_id: sensor.puregym_andover_people_in_gym
        below: 30
    condition:
      - condition: time
        after: "06:00:00"
        before: "21:00:00"
    action:
      - service: notify.notify
        data:
          message: "PureGym has {{ states('sensor.puregym_andover_people_in_gym') }} people in right now."
```

## Credits

API details follow [2t6h/puregym-attendance](https://github.com/2t6h/puregym-attendance).
