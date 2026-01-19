export const EVENT_TYPES = {
    DB_UPDATE: 'db_update',
    ATOM_UPDATE: 'update',
    THREAD_NEW: 'thread_new',
    WORLD_RESET: 'world_reset',
    ENVELOPE_UPDATE: 'envelope_update',
    ENVELOPE_DELETE: 'envelope_delete',
    WORLD_EJECTED: 'world_ejected',
    CONNECTED: 'connected'
};

export const SYNC_EVENTS = [
    EVENT_TYPES.DB_UPDATE,
    EVENT_TYPES.ATOM_UPDATE,
    EVENT_TYPES.THREAD_NEW,
    EVENT_TYPES.WORLD_RESET,
    EVENT_TYPES.ENVELOPE_UPDATE,
    EVENT_TYPES.ENVELOPE_DELETE,
    EVENT_TYPES.WORLD_EJECTED
];
