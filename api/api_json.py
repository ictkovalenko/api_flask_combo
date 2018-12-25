from api.helpers import id_out


def api_isoformat(d):
    if d is None:
        return None
    else:
        return d.isoformat()


def api_json_from_sensor(sensor):
    return {'id': id_out(sensor.id),
            'mac': sensor.remote_details.mac_string(),
            'short_name': sensor.remote_details.short_name(),
            'run_state_current': 1 - sensor.remote_details.sensor_state,
            'run_state_requested': sensor.remote_details.activated,
            'in_pool': [],
            'battery': {'days_left': 90,
                        'days': 0,
                        'voltage': 3.0},
            'lifetime_state': 1,
            'last_seen': api_isoformat(sensor.remote_details.last_seen),
            'last_synced_time': api_isoformat(sensor.remote_details.last_record_received),
            'last_synced_timestamp': api_isoformat(sensor.remote_details.last_record_timestamp),
            'description': 'Real world sensor',
            'type': 'sens/plus',
            'run_time': sensor.remote_details.run_time().total_seconds(),
            'firmware_version': sensor.remote_details.firmware_version,
            'licence': {'class': 'unlimited'}
            }


def api_json_from_sensor_remote_details(remote_details):
    return {'id': id_out(remote_details.id),
            'mac': remote_details.mac_string(),
            'short_name': remote_details.short_name(),
            'run_state_current': 1 - remote_details.sensor_state,
            'run_state_requested': remote_details.activated,
            'battery': {'days_left': 90,
                        'days': 0,
                        'voltage': 3.0},
            'lifetime_state': 2 if remote_details.terminated else 1,
            'last_seen': api_isoformat(remote_details.last_seen),
            'last_synced_time': api_isoformat(remote_details.last_record_received),
            'last_synced_timestamp': api_isoformat(remote_details.last_record_timestamp),
            'type': 'sens/plus',
            'delivery': remote_details.delivery,
            'run_time': remote_details.run_time().total_seconds(),
            'firmware_version': remote_details.firmware_version,
            'licence': {'class': 'unlimited'}
            }


def api_json_from_sensor_pool(pool):
        return {
                'id': id_out(pool.id),
                'short_name': pool.short_name,
                'full_name': pool.name
                }


def api_json_from_measurement(m):
    return {'id': id_out(m.id),
            'start_time': api_isoformat(m.start_time),
            'end_time': api_isoformat(m.end_time),
            'profile': m.profile.name,
            'patient': api_json_from_patient(m.patient),
            'places': [
                {'place': s.place,
                 'short_name': s.sensor.remote_details.short_name(),
                 'id': id_out(s.sensor.id)
                 } for s in m.attached
            ]}


def api_json_from_patient(p):
    return {'id': id_out(p.id),
            'short_name': p.short_name,
            'description': p.description,
            'profile': p.profile.short_name if p.profile else None,
            }
