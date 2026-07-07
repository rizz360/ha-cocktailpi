# Changelog

## [0.5.1](https://github.com/rizz360/ha-cocktailpi/compare/ha-cocktailpi-v0.5.0...ha-cocktailpi-v0.5.1) (2026-07-07)


### Bug Fixes

* report only the version string as the hub's sw_version ([0650f5a](https://github.com/rizz360/ha-cocktailpi/commit/0650f5af02b8eb25057d1fa5e5e0f5aeb02e5ac1))

## [0.5.0](https://github.com/rizz360/ha-cocktailpi/compare/ha-cocktailpi-v0.4.0...ha-cocktailpi-v0.5.0) (2026-07-07)


### Features

* make the polling interval configurable via an options flow ([9e70eed](https://github.com/rizz360/ha-cocktailpi/commit/9e70eed7c95c619a015d9c31446537f7a9f07883)), closes [#4](https://github.com/rizz360/ha-cocktailpi/issues/4)

## [0.4.0](https://github.com/rizz360/ha-cocktailpi/compare/ha-cocktailpi-v0.3.0...ha-cocktailpi-v0.4.0) (2026-07-07)


### Features

* add config entry diagnostics ([263c369](https://github.com/rizz360/ha-cocktailpi/commit/263c369cc4ba3f4d60c6cd90e115565fc34a8c82))
* add German, French, and Spanish translations ([4a68888](https://github.com/rizz360/ha-cocktailpi/commit/4a68888e998f0f964cb7a7200754d2c394153775)), closes [#9](https://github.com/rizz360/ha-cocktailpi/issues/9)
* translate entity names and service strings via strings.json ([8a2a745](https://github.com/rizz360/ha-cocktailpi/commit/8a2a7457b4fef839db91a5a618dc5556dc12ddce)), closes [#5](https://github.com/rizz360/ha-cocktailpi/issues/5)
* trigger reauth flow when CocktailPi credentials stop working ([87c9fb7](https://github.com/rizz360/ha-cocktailpi/commit/87c9fb764bba0f3c112e6d1ef54890b2c1d4a283))


### Bug Fixes

* Distinguish idle-pump WS push from missing running-state data ([f3eb0fe](https://github.com/rizz360/ha-cocktailpi/commit/f3eb0fe52023e9dc484067b8ff36bcdc64a5ced1))

## [0.3.0](https://github.com/rizz360/ha-cocktailpi/compare/ha-cocktailpi-v0.2.0...ha-cocktailpi-v0.3.0) (2026-07-07)


### Features

* Add cancel cocktail button ([6500319](https://github.com/rizz360/ha-cocktailpi/commit/65003190b0fa3ddcd729a3ea98e7999fccc8ae42))
* Add glass-detection binary sensor ([d2db458](https://github.com/rizz360/ha-cocktailpi/commit/d2db458480e37134f9d190eda9dc96ae2ff56585))
* Add GPIO/I2C health binary sensor ([d96e1f2](https://github.com/rizz360/ha-cocktailpi/commit/d96e1f23e9d889d8150b6e5bc84ee487b43eb859))
* Add load-cell weight sensor ([afac889](https://github.com/rizz360/ha-cocktailpi/commit/afac889e6eb2a391423d8e95830c33aa773fd664))

## [0.2.0](https://github.com/rizz360/ha-cocktailpi/compare/ha-cocktailpi-v0.1.0...ha-cocktailpi-v0.2.0) (2026-07-06)


### Features

* Add cocktail progress and state sensors to the CocktailPi integration ([927b4f1](https://github.com/rizz360/ha-cocktailpi/commit/927b4f1b5bc54233a1418dfeff756124161a06f4))
* Add release automation configuration with Release Please ([17873a7](https://github.com/rizz360/ha-cocktailpi/commit/17873a789db9a523b34c3657edf4e95feb2e4045))
* Move from 1 device per pump to single device for all entities ([f46de2b](https://github.com/rizz360/ha-cocktailpi/commit/f46de2b6f4bdc8a03f70c75fbd86ea82f9a25d0b))
