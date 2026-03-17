/**
 * Solar parks (AgriSolarPark): selector, list of trackers per park, create park form.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardContent, CardTitle, Button } from '@nekazari/ui-kit';
import { useTranslation, useViewerOptional } from '@nekazari/sdk';

interface ParkSummary {
    park_id: string;
    name: string;
    ref_agri_parcel: string;
    parcel_name?: string;
    tracker_count: number;
    tracker_ids: string[];
}

interface ParkTrackerItem {
    tracker_id: string;
    name?: string;
}

interface ParcelItem {
    id: string;
    name: string;
}

function fetchWithAuth(path: string, init?: RequestInit): Promise<Response> {
    return fetch(path, { credentials: 'include', ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } });
}

export const SolarParksSection: React.FC = () => {
    const { t } = useTranslation();
    const viewer = useViewerOptional();
    const [parks, setParks] = useState<ParkSummary[]>([]);
    const [parcels, setParcels] = useState<ParcelItem[]>([]);
    const [selectedParkId, setSelectedParkId] = useState<string | null>(null);
    const [trackers, setTrackers] = useState<ParkTrackerItem[]>([]);
    const [loadingParks, setLoadingParks] = useState(false);
    const [loadingTrackers, setLoadingTrackers] = useState(false);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [createName, setCreateName] = useState('');
    const [createParcelId, setCreateParcelId] = useState('');
    const [creating, setCreating] = useState(false);
    const [createError, setCreateError] = useState<string | null>(null);

    const fetchParks = useCallback(async () => {
        setLoadingParks(true);
        try {
            const res = await fetchWithAuth('/api/agrienergy/parks');
            if (res.ok) {
                const data = await res.json();
                setParks(data.parks || []);
            }
        } catch {
            setParks([]);
        } finally {
            setLoadingParks(false);
        }
    }, [fetchWithAuth]);

    const fetchParcels = useCallback(async () => {
        try {
            const res = await fetchWithAuth('/api/agrienergy/parcels');
            if (res.ok) {
                const data = await res.json();
                setParcels(data.parcels || []);
            }
        } catch {
            setParcels([]);
        }
    }, [fetchWithAuth]);

    useEffect(() => {
        fetchParks();
        fetchParcels();
    }, [fetchParks, fetchParcels]);

    useEffect(() => {
        if (!selectedParkId) {
            setTrackers([]);
            return;
        }
        setLoadingTrackers(true);
        fetchWithAuth(`/api/agrienergy/parks/${encodeURIComponent(selectedParkId)}/trackers`)
            .then((res: Response) => (res.ok ? res.json() : { trackers: [] }))
            .then((data: { trackers?: ParkTrackerItem[] }) => setTrackers(data.trackers || []))
            .catch(() => setTrackers([]))
            .finally(() => setLoadingTrackers(false));
    }, [selectedParkId, fetchWithAuth]);

    const handleCreatePark = async () => {
        if (!createName.trim() || !createParcelId.trim()) return;
        setCreating(true);
        setCreateError(null);
        try {
            const res = await fetchWithAuth('/api/agrienergy/parks', {
                method: 'POST',
                body: JSON.stringify({ name: createName.trim(), ref_agri_parcel: createParcelId }),
            });
            if (res.ok) {
                setShowCreateForm(false);
                setCreateName('');
                setCreateParcelId('');
                fetchParks();
            } else {
                const data = await res.json().catch(() => ({}));
                setCreateError(data.detail || t('agrienergy.parks.createError'));
            }
        } catch {
            setCreateError(t('agrienergy.parks.createError'));
        } finally {
            setCreating(false);
        }
    };

    const selectTracker = (trackerId: string) => {
        viewer?.selectEntity?.(trackerId, 'AgriEnergyTracker');
    };

    return (
        <Card className="bg-white dark:bg-gray-800 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-sm">{t('agrienergy.parks.title')}</CardTitle>
                <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => { setShowCreateForm(!showCreateForm); setCreateError(null); }}
                >
                    {showCreateForm ? t('agrienergy.parks.cancel') : t('agrienergy.parks.createPark')}
                </Button>
            </CardHeader>
            <CardContent className="space-y-3">
                {showCreateForm && (
                    <div className="rounded border border-gray-200 dark:border-gray-600 p-3 space-y-2">
                        <label className="text-xs font-medium block">{t('agrienergy.parks.parkName')}</label>
                        <input
                            type="text"
                            value={createName}
                            onChange={(e) => setCreateName(e.target.value)}
                            placeholder={t('agrienergy.parks.parkNamePlaceholder')}
                            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
                        />
                        <label className="text-xs font-medium block">{t('agrienergy.parks.selectParcel')}</label>
                        <select
                            value={createParcelId}
                            onChange={(e) => setCreateParcelId(e.target.value)}
                            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
                        >
                            <option value="">{t('agrienergy.parks.selectParcel')}</option>
                            {parcels.map((p) => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                        {parcels.length === 0 && (
                            <p className="text-xs text-amber-600">{t('agrienergy.parks.noParcels')}</p>
                        )}
                        <Button
                            size="sm"
                            onClick={handleCreatePark}
                            disabled={creating || !createName.trim() || !createParcelId.trim()}
                            className="w-full"
                        >
                            {creating ? t('common.loading') : t('agrienergy.parks.create')}
                        </Button>
                        {createError && (
                            <p className="text-xs text-red-600">{createError}</p>
                        )}
                    </div>
                )}

                {loadingParks && <p className="text-xs text-gray-500">{t('common.loading')}</p>}
                {!loadingParks && parks.length === 0 && !showCreateForm && (
                    <p className="text-xs text-gray-500">{t('agrienergy.parks.noParks')}</p>
                )}
                {!loadingParks && parks.length > 0 && (
                    <>
                        <label className="text-xs font-medium block">{t('agrienergy.parks.selectPark')}</label>
                        <select
                            value={selectedParkId ?? ''}
                            onChange={(e) => setSelectedParkId(e.target.value || null)}
                            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1 text-sm"
                        >
                            <option value="">{t('agrienergy.parks.selectPark')}</option>
                            {parks.map((p) => (
                                <option key={p.park_id} value={p.park_id}>
                                    {p.name} — {p.tracker_count} {t('agrienergy.parks.trackers')}
                                </option>
                            ))}
                        </select>
                        {selectedParkId && (
                            <div className="text-xs">
                                <span className="text-gray-500 block">{t('agrienergy.parks.trackersInPark')}</span>
                                {loadingTrackers && <p className="text-gray-400">{t('common.loading')}</p>}
                                {!loadingTrackers && trackers.length === 0 && (
                                    <p className="text-gray-500">{t('agrienergy.parks.noTrackersInPark')}</p>
                                )}
                                {!loadingTrackers && trackers.length > 0 && (
                                    <ul className="mt-1 space-y-0.5">
                                        {trackers.map((tr) => (
                                            <li key={tr.tracker_id}>
                                                <button
                                                    type="button"
                                                    onClick={() => selectTracker(tr.tracker_id)}
                                                    className="text-left text-blue-600 hover:underline font-mono"
                                                >
                                                    {tr.name || tr.tracker_id}
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
};
