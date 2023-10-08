import requests

from hdhr_dvr.model import Storage


class StorageDiscovery:
    @staticmethod
    def discover_storage():
        session = requests.Session()

        storages = []
        with session.get(f'https://api.hdhomerun.com/discover') as request:
            content = request.json()
            for device in content:
                if device.get('StorageID'):
                    with session.get(device['DiscoverURL']) as storage_request:
                        storage_content = storage_request.json()
                        storages.append(Storage(device['StorageID'], storage_content['FriendlyName'],
                                                device['BaseURL'], device['DiscoverURL'],
                                                device['StorageURL'], storage_content['TotalSpace'],
                                                storage_content['FreeSpace']))

        return storages
