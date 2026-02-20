def seconds_to_bars(bpm, seconds):
    return bpm*(seconds/60)/4

def bars_to_seconds(bpm, bars):
    return ((bars*4)/bpm)*60

def seconds_to_bars_with_changes(bpm_changes, seconds):
    # bpm_changes = [(0, bpm), (time_in_bars, bpm), ...]
    bpm_changes_seconds = [(bars_to_seconds_with_changes(bpm_changes, time), bpm) for time, bpm, in bpm_changes]
    total_bars = 0
    remaining_seconds = seconds
    for current_time, current_bpm in bpm_changes_seconds[::-1]:
        if current_time < remaining_seconds:
            total_bars += seconds_to_bars(current_bpm, remaining_seconds - current_time)
            remaining_seconds = current_time
    return total_bars

def bars_to_seconds_with_changes(bpm_changes, bars):
    # bpm_changes = [(0, bpm), (time_in_bars, bpm), ...]
    total_seconds = 0
    remaining_bars = bars
    for current_time, current_bpm in bpm_changes[::-1]:
        if current_time < remaining_bars:
            total_seconds += bars_to_seconds(current_bpm, remaining_bars - current_time)
            remaining_bars = current_time
    return total_seconds