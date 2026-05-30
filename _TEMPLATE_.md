# VOICE PROFILE: {NOME_DO_LOCUTOR}

> **Slug:** `{slug}`
> **Categoria:** `{categoria}`
> **Versão do DNA:** `{version}`
> **Última atualização:** `{YYYY-MM-DD}`

---

## 1. IDENTIDADE DA VOZ

| Campo | Valor |
|---|---|
| **Nome comercial** | {nome} |
| **Descrição/tagline** | "{descricao}" |
| **Voz base Gemini** | `{voice_name}` |
| **Modelo TTS** | `{model_to_use}` |
| **Status** | `{status}` |
| **Premium?** | `{is_premium}` |
| **Locutor humano referência** | {se houver} |

### Personalidade

```json
{
  "traits": ["{trait1}", "{trait2}", "{trait3}"],
  "vibe": "{vibe}",
  "estilo_vocal": "{estilo_vocal}",
  "tom_sugerido": "{tom_sugerido}",
  "faixa_etaria": "{faixa_etaria_sugerida}",
  "genero_ideal": "{genero_ideal}"
}
```

### Frase de Efeito

> "{frase_de_efeito}"

---

## 2. PARÂMETROS DE CONSISTÊNCIA

### Generation Config

| Parâmetro | Valor | Por quê? |
|---|---|---|
| `temperature` | `{temp}` | {justificativa_temp} |
| `topP` | `{topP}` | {justificativa_topP} |
| `topK` | `{topK}` | {justificativa_topK} |
| `seed` | `{seed}` | {justificativa_seed} |

> **Nota:** Seed fixo é o principal fator de consistência de timbre. Nunca alterar sem testar exaustivamente.

### Audio Output

| Parâmetro | Valor |
|---|---|
| `loudness_target` | `{loudness}` LUFS |

### Speech Config

| Parâmetro | Valor |
|---|---|
| `voice_name` | `{voice_name}` |
| `locale` | `{locale}` |

---

## 3. PERFORMANCE

### Sliders de Atuação

| Parâmetro | Valor | Descrição |
|---|---|---|
| Velocidade padrão | `{velocidade_padrao}`x | {observacao_velocidade} |
| Energia | `{energia_selecionada}`/10 | {observacao_energia} |
| Humanização | `{humanization_level}`/5 | {observacao_humanizacao} |
| Sotaque | `{sotaque}` | {observacao_sotaque} |
| Sorriso na voz | `{sorriso_na_voz}` | {observacao_sorriso} |
| Respiração | `{respiracao}` | {observacao_respiracao} |

### Notas de Performance

{notas_performance}

---

## 4. STUDIO FX CHAIN

| FX | Ativo | Valor | Obs |
|---|---|---|---|
| **Microfone** | sim | `{mic_model}` | Distância: {mic_distance}cm |
| **Analog Warmth** | `{warmth_active}` | `{warmth}` | {obs_warmth} |
| **Room Reverb** | `{reverb_active}` | `{reverb}` | {obs_reverb} |
| **Delay** | `{delay_active}` | `{delay_time}ms / {delay_feedback}% / {delay_mix}%` | {obs_delay} |
| **EQ pós** | — | {eq_settings} | {obs_eq} |

### Mix Notes

{mix_notes}

---

## 5. DIRETRIZES DE ATUAÇÃO (System Instruction)

### Resumo da Diretriz

> {resumo_diretriz}

### O que funciona

- {funciona_1}
- {funciona_2}
- {funciona_3}

### O que evitar

- {evitar_1}
- {evitar_2}
- {evitar_3}

---

## 6. USO RECOMENDADO

| Contexto | Nota (1-5) | Observação |
|---|---|---|
| Spot de rádio | `{nota_spot_radio}` | |
| Chamada de festa | `{nota_festa}` | |
| Comercial TV | `{nota_tv}` | |
| Instagram/Reels | `{nota_reels}` | |
| Narração institucional | `{nota_institucional}` | |
| Podcast/VT | `{nota_podcast}` | |
| Carro de som | `{nota_carro_som}` | |
| Personagem | `{nota_personagem}` | |

---

## 7. HISTÓRICO DE AJUSTES

### {YYYY-MM-DD} — {título da mudança}

**Contexto:** {por que mudou}
**O que mudou:**
- {mudança_1}
- {mudança_2}
**Resultado:** {resultado_auditivo}
**Aprovação:** {quem aprovou}

---

### {YYYY-MM-DD} — Criação do Perfil

**Contexto:** {motivo da criação}
**Parâmetros iniciais:** seed `{seed_original}`, modelo `{modelo_original}`, temp `{temp_original}`
**Observação:** {obs_criacao}

---

## 8. TESTES DE CONSISTÊNCIA

### Último Teste: {YYYY-MM-DD}

**Frase de teste:** "{frase_de_teste}"
**Seed usada:** `{seed_teste}`
**Modelo:** `{modelo_teste}`
**Resultado:** {resultado_teste}
**Decisão:** {decisao}

### Variações Testadas

| Seed | Temp | Resultado |
|---|---|---|
| `{seed_a}` | `{temp_a}` | {resultado_a} |
| `{seed_b}` | `{temp_b}` | {resultado_b} |

---

## 9. DEPENDÊNCIAS

- **JSON profile:** `studio-hub/categorias/{categoria}/locutores/{slug}.json`
- **Foto:** `assets/images/novos-locutores/{slug}.{ext}`
- **Demo áudio:** `assets/audio/demo/{slug}.wav`
- **Voz base:** `{voice_name}` — compartilhada com: {outros_locutores_usando_mesma_voz}

---

## 10. METADADOS DO ARQUIVO

| Campo | Valor |
|---|---|
| Arquivo | `docs/voices/{slug}.md` |
| Última revisão por | `{autor}` |
| Próxima revisão | `{YYYY-MM-DD}` |
| Tags | `{tag1}`, `{tag2}`, `{tag3}` |
