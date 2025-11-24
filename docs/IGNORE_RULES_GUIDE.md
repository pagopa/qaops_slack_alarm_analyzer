# Ignore Rules - Guida Completa

## Sommario

Le Ignore Rules permettono di filtrare gli allarmi in modo intelligente. Ogni regola può specificare **quando è valida** (`validity`) e **quando NON è valida** (`exclusions`).

## Struttura Base

```yaml
- name: "Nome-Allarme"
  path: "attachments.title.alarm_name"  # Opzionale, default: "*"
  environments: ["prod"]  # Opzionale, default: tutti
  reason: "Descrizione del perché ignoriamo questo allarme"

  # OPZIONALE: Specifica quando la regola è valida
  validity:
    periods:   # Periodi temporali
      - start: "2025-01-01"
        end: "2025-01-31"
    weekdays:  # Giorni della settimana
      - "monday"
      - "tuesday"
    hours:     # Orari del giorno
      - start: "01:00"
        end: "05:00"

  # OPZIONALE: Specifica quando la regola NON è valida (inverso)
  exclusions:
    periods:   # Stessa struttura di validity
      - start: "2025-12-24"
        end: "2025-12-26"
    weekdays:
      - "saturday"
      - "sunday"
    hours:
      - start: "12:00"
        end: "14:00"
```

## Campo `validity` (Quando la regola è valida)

Il campo `validity` definisce QUANDO la regola deve essere applicata. Se specifichi `validity`, la regola sarà attiva **SOLO** quando tutti i criteri sono soddisfatti.

### Logica di Validazione

- **Nessun campo** = sempre valido (retrocompatibilità)
- **Più criteri** = AND logico (tutti devono matchare)
- **Multipli valori per criterio** = OR logico (basta uno)

### Periods (Periodi Temporali)

Definiscono intervalli di date/datetime.

```yaml
validity:
  periods:
    # Periodo completo
    - start: "2025-01-01"
      end: "2025-01-31"

    # Solo data inizio (valido da quella data in avanti)
    - start: "2025-06-01"

    # Solo data fine (valido fino a quella data)
    - end: "2025-03-31"

    # Con orario specifico
    - start: "2025-01-15 22:00:00"
      end: "2025-01-16 06:00:00"
```

**Logica OR**: Se specifichi multipli periodi, basta che la data corrente ricada in UNO di essi.

### Weekdays (Giorni della Settimana)

Definiscono i giorni della settimana in cui la regola è valida.

```yaml
validity:
  weekdays:
    # Usa nomi in inglese
    - "monday"
    - "tuesday"
    - "wednesday"
    - "thursday"
    - "friday"

    # Oppure numeri (0=Monday, 6=Sunday)
    - 0  # Lunedì
    - 1  # Martedì
    - 5  # Sabato

    # Abbreviazioni supportate
    - "mon"
    - "tue"
    - "wed"
```

**Logica OR**: La regola è valida se il giorno corrente è UNO di quelli specificati.

### Hours (Orari del Giorno)

Definiscono gli orari in cui la regola è valida.

```yaml
validity:
  hours:
    # Orario singolo
    - start: "01:00"
      end: "05:00"

    # Multipli orari
    - start: "09:00"
      end: "12:00"
    - start: "14:00"
      end: "17:00"

    # Range che attraversa la mezzanotte
    - start: "22:00"
      end: "02:00"
```

**Logica OR**: La regola è valida se l'ora corrente ricade in ALMENO UNO dei range.

### Combinare Più Criteri (AND Logico)

Quando specifichi più criteri in `validity`, **TUTTI** devono essere soddisfatti:

```yaml
validity:
  periods:
    - start: "2025-11-01"
      end: "2025-12-31"
  weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday"]
  hours:
    - start: "00:00"
      end: "08:00"
```

Questa regola è valida SOLO quando:
- La data è tra 1 Nov e 31 Dic 2025 **E**
- Il giorno è Lun-Ven **E**
- L'orario è tra 00:00-08:00

## Campo `exclusions` (Quando la regola NON è valida)

Il campo `exclusions` è l'inverso di `validity`. Se specifichi `exclusions`, la regola **NON** sarà applicata quando i criteri sono soddisfatti.

### Esempi di Exclusions

#### Escludi i weekend

```yaml
- name: "Business-Hours-Alert"
  path: "attachments.title"
  exclusions:
    weekdays: ["saturday", "sunday"]
  reason: "Ignora questo allarme nei giorni feriali, ma NON nel weekend"
```

La regola è valida sempre **TRANNE** Sabato e Domenica.

#### Escludi la pausa pranzo

```yaml
- name: "Work-Alert"
  path: "attachments.title"
  exclusions:
    hours:
      - start: "12:00"
        end: "14:00"
  reason: "Valido sempre tranne durante la pausa pranzo"
```

#### Escludi periodo festivo

```yaml
- name: "Normal-Alert"
  path: "attachments.title"
  exclusions:
    periods:
      - start: "2025-12-24"
        end: "2025-12-26"
  reason: "Valido sempre tranne durante le festività natalizie"
```

## Combinare `validity` e `exclusions`

Puoi usare entrambi per creare regole molto precise:

```yaml
- name: "Business-Hours-Alert"
  path: "attachments.title"
  validity:
    weekdays: [0, 1, 2, 3, 4]  # Lun-Ven
    hours:
      - start: "08:00"
        end: "18:00"
  exclusions:
    hours:
      - start: "12:00"
        end: "13:00"  # Pausa pranzo
  reason: "Valido in orario lavorativo (8-18, Lun-Ven) tranne la pausa pranzo"
```

Questa regola è valida quando:
- È un giorno feriale (Lun-Ven) **E**
- L'orario è 08:00-18:00 **MA NON** 12:00-13:00

## Esempi Pratici Completi

### Esempio 1: Allarme Temporaneo (fino a una data)

```yaml
- name: "pn-web-logout-api-ErrorAlarm"
  path: "attachments.title.alarm_name"
  validity:
    periods:
      - end: "2025-11-06"
  reason: "Fino al prossimo rilascio in prod (6 novembre 2025)"
```

### Esempio 2: Allarmi Notturni Periodici

```yaml
- name: "workday-SLAViolations-SendPaperAr890-Alarm"
  path: "attachments.title.alarm_name"
  validity:
    hours:
      - start: "01:00"
        end: "05:00"
  reason: "Questi allarmi scattano ogni giorno alle 3.00 UTC"
```

### Esempio 3: Solo nei Giorni Feriali

```yaml
- name: "Weekday-Only-Alert"
  path: "attachments.title"
  validity:
    weekdays: ["monday", "tuesday", "wednesday", "thursday", "friday"]
  reason: "Ignora solo nei giorni feriali"
```

### Esempio 4: Solo nei Weekend

```yaml
- name: "Weekend-Batch-Alert"
  path: "attachments.title"
  validity:
    weekdays: ["saturday", "sunday"]
  reason: "Ignora solo nel weekend quando girano i batch"
```

### Esempio 5: Periodo con Eccezioni

```yaml
- name: "Seasonal-Alert"
  path: "attachments.title"
  validity:
    periods:
      - start: "2025-06-01"
        end: "2025-08-31"
  exclusions:
    weekdays: ["saturday", "sunday"]
  reason: "Durante l'estate (Giu-Ago) ma NON nei weekend"
```

### Esempio 6: Orario Lavorativo con Pausa Pranzo

```yaml
- name: "Office-Hours-Alert"
  path: "attachments.title"
  validity:
    weekdays: [0, 1, 2, 3, 4]
    hours:
      - start: "09:00"
        end: "18:00"
  exclusions:
    hours:
      - start: "12:30"
        end: "14:00"
  reason: "Orario ufficio (9-18, Lun-Ven) esclusa pausa pranzo"
```

### Esempio 7: Multipli Periodi Stagionali

```yaml
- name: "Seasonal-Load-Alert"
  path: "attachments.title"
  validity:
    periods:
      - start: "2025-01-01"
        end: "2025-03-31"  # Q1
      - start: "2025-06-01"
        end: "2025-08-31"  # Estate
    weekdays: [0, 1, 2, 3, 4]
  reason: "Durante Q1 e estate, solo nei giorni feriali"
```

### Esempio 8: Turni di Notte

```yaml
- name: "Night-Shift-Alert"
  path: "attachments.title"
  validity:
    hours:
      - start: "22:00"
        end: "06:00"  # Attraversa la mezzanotte
  exclusions:
    weekdays: ["saturday", "sunday"]
  reason: "Turno notturno (22-06) ma non nel weekend"
```

### Esempio 9: Manutenzione Programmata

```yaml
- name: "Maintenance-Window-Alert"
  path: "attachments.title"
  validity:
    periods:
      - start: "2025-01-15 02:00:00"
        end: "2025-01-15 04:00:00"
  reason: "Finestra di manutenzione specifica"
```

### Esempio 10: Black Friday

```yaml
- name: "High-Load-Warning"
  path: "attachments.title"
  validity:
    periods:
      - start: "2025-11-20"
        end: "2025-11-30"
    hours:
      - start: "18:00"
        end: "23:59"
  reason: "Durante il Black Friday, ignora warning di carico alto nelle ore serali"
```

## Regole Senza Vincoli Temporali

Le regole senza `validity` o `exclusions` sono sempre valide:

```yaml
- name: "AWS Notification Message"
  path: "files.name"
  reason: "Sempre ignorato"
```

## Riferimento Rapido

### Weekdays
- **Nomi**: monday, tuesday, wednesday, thursday, friday, saturday, sunday
- **Abbreviazioni**: mon, tue, wed, thu, fri, sat, sun
- **Numeri**: 0 (Monday) - 6 (Sunday)

### Formati Date/Time
- **Solo data**: `YYYY-MM-DD` (es. `2025-01-31`)
- **Data e ora**: `YYYY-MM-DD HH:MM:SS` (es. `2025-01-31 23:59:59`)
- **Data e ora breve**: `YYYY-MM-DD HH:MM` (es. `2025-01-31 23:59`)

### Formati Orari
- **Formato**: `HH:MM` in formato 24 ore
- **Esempi**: `01:00`, `14:30`, `23:59`

## Best Practices

1. **Usa `validity` quando sai quando applicare la regola**
   - Allarmi notturni periodici
   - Periodi di manutenzione
   - Regole temporanee con data di scadenza

2. **Usa `exclusions` quando è più facile definire le eccezioni**
   - "Sempre tranne i weekend"
   - "Sempre tranne la pausa pranzo"
   - "Sempre tranne durante le festività"

3. **Combina entrambi per regole complesse**
   - "Orario lavorativo tranne pausa pranzo"
   - "Periodo estivo tranne weekend"

4. **Documenta sempre con `reason`**
   - Spiega perché la regola esiste
   - Include date importanti o link a ticket

5. **Testa le tue regole**
   - Usa il campo `reason` per documentare casi limite
   - Verifica che la logica AND/OR sia corretta
