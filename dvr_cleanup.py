from collections import defaultdict

from hdhr_dvr.discovery import StorageDiscovery
from hdhr_dvr.model import EpisodeState, Episode

EPISODES_TO_KEEP = 13

storages = StorageDiscovery.discover_storage()
for storage in storages:
    all_series = storage.series()
    for series in all_series:
        episodes = series.episodes()

        if len(episodes) < EPISODES_TO_KEEP:
            continue

        episodes_by_state: dict[EpisodeState, list[Episode]] = defaultdict(lambda: [])
        for episode in episodes:
            episodes_by_state[episode.state].append(episode)
        episodes_by_state[EpisodeState.watched].sort(key=lambda ep: ep.record_start_time)
        episodes_by_state[EpisodeState.partially_watched].sort(key=lambda ep: ep.percent_watched, reverse=True)
        episodes_by_state[EpisodeState.unwatched].sort(key=lambda ep: ep.record_start_time)
        delete_ordered_episodes = episodes_by_state[EpisodeState.watched] + \
                                  episodes_by_state[EpisodeState.partially_watched] + \
                                  episodes_by_state[EpisodeState.unwatched]

        delete_ordered_episodes = delete_ordered_episodes[:-EPISODES_TO_KEEP]
        for episode in delete_ordered_episodes:
            episode.delete()
            print(f'Deleted {episode}')
    storage.poke()
exit(0)
