# Ignore Rules - Guida Rapida

## Introduzione

Le Ignore Rules permettono di filtrare intelligentemente gli allarmi specificando quando una regola deve essere applicata (`validity`) e quando non deve esserlo (`exclusions`).

## Sintassi Base

```yaml
- name: "Nome-Allarme"
  path: "attachments.title.alarm_name"  # Dove cercare (default: "*")
  environments: ["prod"]                # Opzionale: ambienti specifici
  reason: "Perché ignoriamo questo allarme"

  # OPZIONALE: Quando la regola è valida
  validity:
    periods:   # Periodi temporali
      - start: "2025-01-01"
        end: "2025-01-31"
    weekdays:  # Giorni della settimana
      - "monday"
      - "friday"
    hours:     # Orari del giorno
      - start: "01:00"
        end: "05:00"

  # OPZIONALE: Quando la regola NON è valida
  exclusions:
    weekdays: ["saturday", "sunday"]
    hours:
      - start: "12:00"
        end: "14:00"
```

## Esempi Rapidi

### 1. Sempre Valida (no vincoli temporali)
```yaml
- name: "AWS Notification Message"
  path: "files.name"
  reason: "Notifiche AWS non rilevanti"
```

### 2. Valida Solo Fino a Una Data
```yaml
- name: "pn-web-logout-api-ErrorAlarm"
  path: "attachments.title.alarm_name"
  validity:
    periods:
      - end: "2025-11-06"
  reason: "Fino al rilascio del 6 novembre"
```

### 3. Valida Solo Di Notte
```yaml
- name: "workday-SLAViolations-SendPaperAr890-Alarm"
  path: "attachments.title.alarm_name"
  validity:
    hours:
      - start: "01:00"
        end: "05:00"
  reason: "Allarmi che scattano alle 3:00 UTC"
```

### 4. Sempre Tranne Weekend
```yaml
- name: "Business-Alert"
  path: "attachments.title"
  exclusions:
    weekdays: ["saturday", "sunday"]
  reason: "Solo nei giorni lavorativi"
```

### 5. Orario Lavorativo Senza Pausa Pranzo
```yaml
- name: "Office-Hours-Alert"
  path: "attachments.title"
  validity:
    weekdays: [0, 1, 2, 3, 4]  # Lun-Ven
    hours:
      - start: "09:00"
        end: "18:00"
  exclusions:
    hours:
      - start: "12:30"
        end: "14:00"
  reason: "9-18 Lun-Ven, esclusa pausa pranzo"
```

## Logica di Validazione

### Validity (AND tra criteri, OR tra valori)

```yaml
validity:
  periods: [P1, P2]    # Almeno uno dei periodi
  weekdays: [Mon, Tue] # Deve essere lunedì O martedì
  hours: [H1, H2]      # Almeno uno degli orari
```

La regola è valida se: **(P1 OR P2) AND (Mon OR Tue) AND (H1 OR H2)**

### Exclusions (logica inversa)

```yaml
exclusions:
  weekdays: [Sat, Sun]
  hours: [Night]
```

La regola NON è valida se: **(Sat OR Sun) AND Night**

### Risultato Finale

```
Regola Valida = validity_matches AND NOT exclusions_matches
```

## Formati Supportati

### Weekdays
- **Nomi**: monday, tuesday, wednesday, thursday, friday, saturday, sunday
- **Abbreviazioni**: mon, tue, wed, thu, fri, sat, sun
- **Numeri**: 0 (Monday) - 6 (Sunday)

### Date/Time
- **Solo data**: `YYYY-MM-DD` → `2025-01-31`
- **Data e ora**: `YYYY-MM-DD HH:MM:SS` → `2025-01-31 23:59:59`
- **Data e ora breve**: `YYYY-MM-DD HH:MM` → `2025-01-31 23:59`

### Orari
- **Formato 24h**: `HH:MM` → `01:00`, `14:30`, `23:59`
- **Range notturno**: `22:00` - `02:00` (attraversa la mezzanotte)

## Path (Dove Cercare)

- `"*"` - Cerca in tutti i campi (default)
- `"text"` - Solo nel campo text del messaggio
- `"attachments.title"` - Solo nei titoli degli attachments
- `"attachments.title.alarm_name"` - Estrae nome allarme dal titolo SEND
- `"files.name"` - Solo nei nomi dei file

## Environments

```yaml
# Applica a tutti gli ambienti
environments: []  # o ometti il campo

# Solo specifici ambienti
environments: ["prod", "uat"]

# Con placeholder [#env#]
name: "API-Error-[#env#]"  # Diventa: API-Error-prod, API-Error-uat
```

## Best Practices

1. ✅ **Usa sempre `reason`** per documentare perché la regola esiste
2. ✅ **Usa `validity`** quando sai esattamente quando applicare la regola
3. ✅ **Usa `exclusions`** quando è più facile definire le eccezioni
4. ✅ **Combina entrambi** per logica complessa
5. ✅ **Testa le regole** prima del deploy in produzione

## Risorse

- **Guida Completa**: `docs/IGNORE_RULES_GUIDE.md`
- **25+ Esempi**: `config/ignore_rules_examples_v2.yaml`
- **Changelog**: `CHANGELOG.md`
- **Test**: `tests/test_time_constraint.py`

## Quick Reference

```yaml
# Periodo temporale
validity:
  periods:
    - start: "2025-01-01"  # Opzionale
      end: "2025-12-31"    # Opzionale

# Giorni settimana
validity:
  weekdays: ["monday", "friday"]  # O numeri: [0, 4]

# Orari
validity:
  hours:
    - start: "09:00"
      end: "17:00"

# Multipli valori (OR)
validity:
  hours:
    - start: "09:00"
      end: "12:00"
    - start: "14:00"      # Secondo range (OR)
      end: "17:00"

# Combinazione (AND tra criteri)
validity:
  periods: [...]   # Deve matchare almeno un periodo
  weekdays: [...]  # E deve essere uno dei giorni
  hours: [...]     # E deve essere in uno degli orari

# Exclusions (inverso)
exclusions:
  weekdays: ["saturday", "sunday"]  # NON applicare nel weekend
```
