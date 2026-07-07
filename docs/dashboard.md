# Example dashboard

A ready-made Lovelace dashboard for this integration, built with Home Assistant's modern
*sections* view and *tile* cards — no custom (HACS) cards required.

![CocktailPi dashboard](images/dashboard.png)

It has three sections:

- **Now mixing** — the current cocktail, machine state, a progress bar, and glass detection.
  A red **Cancel** tile appears only while an order is active (`ready_to_start`, `running`,
  `manual_ingredient_add`, `manual_action_required`) and stays hidden when idle.
- **Ingredients** — a markdown table listing every pump's loaded ingredient, fill level (mL), and
  a ✅/⚠️ readiness indicator derived from the status sensor's `pump_state` attribute. It updates
  live as levels change.
- **Machine** — an "All pumps" valve tile with open/close controls, a compact grid of the
  individual pump valves (tap opens details rather than toggling, so a stray tap can't dispense),
  plus the load-cell weight and firmware update tiles.

Badges at the top show the cocktail state and glass detection, and an update badge that is only
visible when a CocktailPi update is available.

## Using it

1. Create a new dashboard (**Settings → Dashboards → Add Dashboard → New dashboard from
   scratch**), open it, then **✎ Edit → ⋮ → Raw configuration editor**.
2. Paste the YAML below and save.

Entity IDs below assume the default device name (`CocktailPi`) and eight low-flow pumps. If you
renamed the device or have a different pump setup, adjust the `cocktailpi_low_flow_*` IDs and the
`range(1, 9)` in the markdown template accordingly. High-flow pump valves (e.g.
`valve.cocktailpi_high_flow_1`) can be added to the **Machine** section the same way as the
low-flow ones — they are disabled by default in Home Assistant until you enable the entities.

```yaml
views:
  - title: Bar
    path: bar
    icon: mdi:glass-cocktail
    type: sections
    max_columns: 3
    badges:
      - type: entity
        entity: sensor.cocktailpi_cocktail_state
        show_name: false
        show_state: true
        color: purple
      - type: entity
        entity: binary_sensor.cocktailpi_glass_detected
        show_name: true
        show_state: true
      - type: entity
        entity: update.cocktailpi_update
        visibility:
          - condition: state
            entity: update.cocktailpi_update
            state: "on"
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Now mixing
            heading_style: title
            icon: mdi:shaker
          - type: tile
            entity: sensor.cocktailpi_current_cocktail
            name: Cocktail
            color: purple
            grid_options:
              columns: 6
          - type: tile
            entity: sensor.cocktailpi_cocktail_state
            name: State
            color: indigo
            grid_options:
              columns: 6
          - type: tile
            entity: sensor.cocktailpi_cocktail_progress
            name: Progress
            color: green
            features:
              - type: bar-gauge
            grid_options:
              columns: full
          - type: tile
            entity: binary_sensor.cocktailpi_glass_detected
            name: Glass
            color: cyan
            grid_options:
              columns: 6
          - type: tile
            entity: button.cocktailpi_cancel_cocktail
            name: Cancel
            color: red
            icon: mdi:stop-circle-outline
            tap_action:
              action: toggle
            grid_options:
              columns: 6
            visibility:
              - condition: state
                entity: sensor.cocktailpi_cocktail_state
                state:
                  - ready_to_start
                  - running
                  - manual_ingredient_add
                  - manual_action_required
      - type: grid
        cards:
          - type: heading
            heading: Ingredients
            heading_style: title
            icon: mdi:bottle-tonic-outline
          - type: markdown
            grid_options:
              columns: full
            content: >-
              | # | Ingredient | Level | Pump |

              |:-:|:--|--:|:-:|

              {% for i in range(1, 9) %}{% set s = 'sensor.cocktailpi_low_flow_' ~ i ~ '_status'
              %}{% set l = 'sensor.cocktailpi_low_flow_' ~ i ~ '_fill_level' %}| {{ i }} |
              **{{ states(s) }}** | {{ states(l) }} mL | {{ '✅' if state_attr(s, 'pump_state')
              == 'READY' else '⚠️ ' ~ (state_attr(s, 'pump_state') or 'unknown') }} |

              {% endfor %}
            entity_id:
              - sensor.cocktailpi_low_flow_1_status
              - sensor.cocktailpi_low_flow_1_fill_level
              - sensor.cocktailpi_low_flow_2_status
              - sensor.cocktailpi_low_flow_2_fill_level
              - sensor.cocktailpi_low_flow_3_status
              - sensor.cocktailpi_low_flow_3_fill_level
              - sensor.cocktailpi_low_flow_4_status
              - sensor.cocktailpi_low_flow_4_fill_level
              - sensor.cocktailpi_low_flow_5_status
              - sensor.cocktailpi_low_flow_5_fill_level
              - sensor.cocktailpi_low_flow_6_status
              - sensor.cocktailpi_low_flow_6_fill_level
              - sensor.cocktailpi_low_flow_7_status
              - sensor.cocktailpi_low_flow_7_fill_level
              - sensor.cocktailpi_low_flow_8_status
              - sensor.cocktailpi_low_flow_8_fill_level
      - type: grid
        cards:
          - type: heading
            heading: Machine
            heading_style: title
            icon: mdi:pump
          - type: tile
            entity: valve.cocktailpi_all_pumps
            name: All pumps
            color: amber
            features:
              - type: valve-open-close
            grid_options:
              columns: full
          - type: tile
            entity: valve.cocktailpi_low_flow_1
            name: Pump 1
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_2
            name: Pump 2
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_3
            name: Pump 3
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_4
            name: Pump 4
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_5
            name: Pump 5
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_6
            name: Pump 6
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_7
            name: Pump 7
            grid_options:
              columns: 3
          - type: tile
            entity: valve.cocktailpi_low_flow_8
            name: Pump 8
            grid_options:
              columns: 3
          - type: tile
            entity: sensor.cocktailpi_load_cell_weight
            name: Load cell
            grid_options:
              columns: 6
          - type: tile
            entity: update.cocktailpi_update
            name: Firmware
            grid_options:
              columns: 6
```

## Notes

- The markdown card is the only built-in card that renders Jinja2 templates, which is what makes
  the combined ingredient + fill-level + readiness table possible without custom cards. The
  `entity_id` list forces re-renders when any of those sensors change, since the card's automatic
  entity detection can't see through the string-built entity IDs in the loop.
- Pump valve states show *Unknown* until the first WebSocket `runningstate` message arrives for
  that pump (see the architecture notes in the README) — that's expected, not a config error.
- To trigger drinks from the dashboard, add a button/shortcut that calls
  `cocktailpi.order_cocktail` with your favourite recipe ID.
