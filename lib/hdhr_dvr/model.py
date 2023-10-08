from enum import Enum

import requests
from retry import retry


class Storage:
    id = None
    name = None
    base_url = None
    discovery_url = None
    storage_url = None
    total_space = 0
    free_space = 0

    @property
    def utilization(self):
        return f'{100 * self.free_space / self.total_space:.0f}'

    def __str__(self):
        return f'{self.name}@{self.base_url} ({self.utilization}% free)'

    def __repr__(self):
        return str(self)

    def __init__(self, id, name, base_url, discovery_url, storage_url, total_space, free_space):
        self.id = id
        self.name = name
        self.base_url = base_url
        self.discovery_url = discovery_url
        self.storage_url = storage_url
        self.total_space = total_space
        self.free_space = free_space

    @retry(tries=3, delay=1, backoff=2)
    def series(self):
        session = requests.Session()

        with session.get(f'{self.storage_url}') as request:
            content = request.json()
            # HDHR DVR sometimes duplicates items in the list, so we de-dupe by SeriesID here.
            all_series = {}
            for series in content:
                all_series[series['SeriesID']] = Series(series['SeriesID'], series['Title'], series['EpisodesURL'])
            return all_series.values()

    @retry(tries=3, delay=1, backoff=2)
    def poke(self):
        session = requests.Session()
        with session.post(f'{self.base_url}/recording_events.post?sync') as request:
            request.raise_for_status()


class Series:
    id = None
    title = None
    episodes_url = None

    def __str__(self):
        return f'<Series@{self.id}: {self.title}>'

    def __repr__(self):
        return str(self)

    def __init__(self, id, title, episodes_url):
        self.id = id
        self.title = title
        self.episodes_url = episodes_url

    @retry(tries=3, delay=1, backoff=2)
    def episodes(self):
        session = requests.Session()

        with session.get(f'{self.episodes_url}') as request:
            episodes = request.json()
            all_episodes = {}
            for episode in episodes:
                episode_id = episode['ProgramID']
                resume = episode.get('Resume', 0)
                title = episode.get('EpisodeTitle', episode.get('Title', 'No title'))
                all_episodes[episode_id] = Episode(self.id, episode_id, self.title, title, episode['RecordStartTime'],
                                                   episode['RecordEndTime'], resume, episode['CmdURL'])

            return all_episodes.values()


class EpisodeState(Enum):
    unwatched = 0
    partially_watched = 1
    watched = 2


class Episode:
    series_id = None
    record_start_time = 0
    record_end_time = 0
    record_duration = 0
    resume_offset = 0
    title = None
    series_title = None
    id = None
    cmd_url = None

    def __str__(self):
        return f'{self.series_title}: {self.title} (start: {self.record_start_time}, {self.percent_watched * 100:.0f}%)'

    def __repr__(self):
        return str(self)

    def __init__(self, series_id, id, series_title, title, record_start_time, record_end_time, resume_offset,
                 cmd_url):
        self.id = id
        self.series_id = series_id
        self.series_title = series_title
        self.title = title
        self.record_start_time = record_start_time
        self.record_end_time = record_end_time
        self.record_duration = record_end_time - record_start_time
        self.resume_offset = resume_offset
        self.cmd_url = cmd_url

    @property
    def state(self) -> EpisodeState:
        if self.resume_offset >= self.record_duration - 150:
            return EpisodeState.watched
        elif self.resume_offset > 0:
            return EpisodeState.partially_watched
        else:
            return EpisodeState.unwatched

    @property
    def percent_watched(self) -> float:
        return self.resume_offset / self.record_duration

    @retry(tries=3, delay=1, backoff=2)
    def delete(self):
        session = requests.Session()

        with session.post(f'{self.cmd_url}', params={
            'cmd': 'delete'
        }) as request:
            request.raise_for_status()
