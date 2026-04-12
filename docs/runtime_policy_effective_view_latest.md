# Runtime Policy Effective View

- Generated: `2026-04-12T17:38:34+00:00`
- Runtime snapshot pulled_at: `2026-04-12T17:37:56.2321397+00:00`
- Effective mode counts: `{'shadow': 18, 'canary': 6, 'blocked': 3}`
- Collision count: `7`
- Collision category counts: `{'documented_drift': 7}`
- Blocking operational collisions: `0`
- Active effective count: `0`

## Contract

`effective_mode` is the operational mode humans and tools should cite. Env lists and runtime auto policy are shown as inputs, not as standalone truth.

Priority: manual blocked, auto blocked, auto shadow, manual active, auto canary, manual canary, default shadow.

## Cities

| City | Env | Runtime | Cross | Effective | Collision | Category | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| amsterdam | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| ankara | shadow | runtime_unknown | blocked | shadow | cross_effective_divergence | documented_drift | default_shadow |
| Atlanta | shadow | auto_canary | unknown | canary | - | documented_drift | city_policy_state.auto_canary_cities |
| buenos aires | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| chicago | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| hong kong | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| houston | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| istanbul | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| London | blocked | runtime_unknown | blocked | blocked | - | - | BLOCKED_CITIES |
| madrid | shadow | runtime_unknown | blocked | shadow | cross_effective_divergence | documented_drift | default_shadow |
| mexico city | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| miami | shadow | runtime_unknown | blocked | shadow | cross_effective_divergence | documented_drift | default_shadow |
| milan | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| moscow | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| Munich | shadow | auto_canary | canary | canary | - | - | city_policy_state.auto_canary_cities |
| New York City | shadow | auto_canary | canary | canary | - | - | city_policy_state.auto_canary_cities |
| paris | shadow | runtime_unknown | blocked | shadow | cross_effective_divergence | documented_drift | default_shadow |
| san francisco | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| seattle | shadow | runtime_unknown | blocked | shadow | cross_effective_divergence | documented_drift | default_shadow |
| Seoul | shadow | auto_canary | canary | canary | - | - | city_policy_state.auto_canary_cities |
| Shanghai | shadow | auto_canary | canary | canary | - | - | city_policy_state.auto_canary_cities |
| shenzhen | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| Singapore | blocked | runtime_unknown | unknown | blocked | - | - | BLOCKED_CITIES |
| Tokyo | shadow | auto_canary | unknown | canary | - | documented_drift | city_policy_state.auto_canary_cities |
| Toronto | blocked | runtime_unknown | blocked | blocked | - | - | BLOCKED_CITIES |
| warsaw | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
| wuhan | shadow | runtime_unknown | shadow | shadow | - | - | default_shadow |
