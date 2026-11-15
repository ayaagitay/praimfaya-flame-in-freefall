# praimfaya-flame-in-freefall
Dashboard that ranks and explains NASA microgravity combustion experiments (BASS-II, FLEX) to inform fire safety for Moon and Mars missions. NASA Space Apps Challenge 2026, Flame in Freefall.

**Link to the dashboard:** https://praimfaya-flame-in-freefall.streamlit.app/

## Dashboard status: hackathon prototype

The dashboard was built in two days for the NASA Space Apps Challenge 2026. It turns
real NASA microgravity combustion data into fire-safety answers, but it is a
**research prototype**, not a certified safety tool.

### What the dashboard does

- Uses two real NASA datasets from the International Space Station: **FLEX** (274
  liquid-fuel droplet tests) and **BASS-II** (129 solid-material tests).
- **Ask the data:** choose a fuel or material and an oxygen level, and see what the
  matching real tests showed. The slider only covers oxygen levels NASA tested. If no
  test matches, the dashboard says so and does not guess.
- **Fuel ranking:** ranks 24 combinations of fuel, added gas and oxygen level by a
  flame intensity index from 0 to 100.
- **FLEX and BASS-II explorers:** charts and raw tables for browsing every test.
- **AI advisory:** Google Gemini writes a one-sentence safety note from the selected
  rows. If the text contains a number that is not in the data, it is discarded and a
  fixed sentence built by our code is shown instead. A label always says which one
  you are reading.
- **Cabin sensor node:** live status, readings and history from the Arduino device.
- **Sources:** where every dataset and label comes from.

### Known limitations

- **The flame intensity index is our own calculation** from the data. It is not a
  NASA number and not a probability of fire.
- **Only two datasets are included.** Many other NASA combustion experiments are not
  covered.
- **Few fuels and materials.** FLEX covers two liquid fuels, and BASS-II covers a
  small set of plastics and fabrics.
- **BASS-II has no flame-spread speed,** so solid materials are described by oxygen
  drop and carbon monoxide rise instead of burning rate.
- **Some rankings rest on very few tests.** These rows carry a warning mark and
  should be read with caution.
- **Results describe small-scale experiments.** They do not directly predict how a
  fire would behave in a full spacecraft cabin.
- **The AI note is a summary,** not expert advice. It can only repeat what is in the
  selected rows.
- **Not reviewed by NASA or by combustion scientists.** This is an independent
  student project.

### What a real version would need

- More datasets (for example Saffire, SAME and ACME) and more materials actually used
  in spacecraft.
- An index designed and validated with combustion experts, with uncertainty shown for
  every value.
- Checks of its answers against published NASA results.
- Links from each answer to the source papers behind it.
- A real inventory of the materials on board, tied to sensor locations.
- Review and testing before any use in mission planning.


## Hardware status: concept prototype

The cabin sensor node in this project is a **concept prototype**. It shows how a small
always-on sensor could work alongside the dashboard. It is not a fire detector and must
not be used for real safety decisions.

### What the prototype does

- Built on a breadboard with an Arduino UNO, a DHT11 temperature sensor, a photoresistor
  (light sensor), three status LEDs and a buzzer.
- Measures **air temperature and light level** only, about once every 2 seconds.
- Raises a warning when temperature rises quickly or reaches 32 °C, and an alarm at
  35 °C or at a very bright light reading.
- Sends each reading to the dashboard as one JSON line over a USB cable.

### Known limitations

- It does not sense smoke, gas or flames. Heat and light are indirect signs only.
- The DHT11 is slow and accurate to about ±2 °C, so it cannot catch a fast, local
  temperature change such as an overheating wire.
- The light sensor reacts to any bright light, so it only makes sense in a dark,
  enclosed space.
- The thresholds were chosen for a demonstration on Earth. They are not based on
  microgravity combustion data.
- It needs a USB connection to a laptop, and the dashboard can only read it when
  running on that same computer.
- It was tested in a room on Earth, never with a real flame and never in microgravity.
- When no device is connected, the dashboard shows simulated readings, clearly
  labelled as simulated.

### What a real version would need

- **Proper fire sensors:** smoke or particle detection, gas sensing (carbon monoxide,
  carbon dioxide, oxygen), and infrared flame sensing, combined so that one false
  reading does not trigger an alarm.
- **Faster, more accurate temperature sensing,** placed directly on wiring and
  equipment instead of measuring room air.
- **Thresholds derived from microgravity research,** where flames are cooler and
  dimmer than on Earth and heat does not rise toward a ceiling detector.
- **Many nodes** placed close to possible fire sources, reporting over a reliable
  network instead of one USB cable.
- **Flight-grade hardware:** a soldered and enclosed board, backup power, self-tests,
  and qualification for vibration, radiation and the cabin atmosphere.
- **Testing and certification** against spacecraft fire-safety standards before any
  use with a crew.


