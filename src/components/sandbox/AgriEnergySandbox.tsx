import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardContent, CardTitle, Button, Alert } from '@nekazari/ui-kit';
import { useApi, useTranslation, useViewer } from '@nekazari/sdk';
import { AlgorithmSelector } from './AlgorithmSelector';
import { ConfigureSignals } from './ConfigureSignals';
import { SolarParksSection } from './SolarParksSection';

const STATUS_POLL_INTERVAL_MS = 10000;

interface SignalMappingRow {
    contextKey: string;
    entityId: string;
    attribute: string;
}

interface TrackerStatus {
    tracker_id: string;
    orientation: { tilt: number; azimuth: number };
    power: { measured_w?: number; expected_w?: number };
    storage?: { soc?: number };
    sensors: Record<string, number>;
    signal_mapping?: SignalMappingRow[] | null;
    active_algorithm_id?: string | null;
    timestamp: string;
}

export const AgriEnergySandbox: React.FC = () => {
    const { fetchWithAuth } = useApi();
    const { t } = useTranslation();
    const { selectedEntityId } = useViewer?.() ?? { selectedEntityId: null };
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [targetTilt, setTargetTilt] = useState<number>(30);
    const [status, setStatus] = useState<TrackerStatus | null>(null);
    const [statusError, setStatusError] = useState<string | null>(null);

    const fetchStatus = useCallback(async () => {
        if (!selectedEntityId) {
            setStatus(null);
            setStatusError(null);
            return;
        }
        try {
            const res = await fetchWithAuth(
                `/api/agrienergy/status?tracker_id=${encodeURIComponent(selectedEntityId)}`
            );
            if (res.ok) {
                const data = await res.json();
                setStatus(data);
                setStatusError(null);
            } else {
                setStatus(null);
                setStatusError('Not found');
            }
        } catch {
            setStatus(null);
            setStatusError(t('agrienergy.panel.noData'));
        }
    }, [selectedEntityId, fetchWithAuth, t]);

    useEffect(() => {
        fetchStatus();
        if (!selectedEntityId) return;
        const id = setInterval(fetchStatus, STATUS_POLL_INTERVAL_MS);
        return () => clearInterval(id);
    }, [selectedEntityId, fetchStatus]);

    const runSimulation = async () => {
        setLoading(true);
        try {
            // Mockup call, in production this maps down to the /simulate endpoint passing entities.
            const res = await fetchWithAuth('/api/agrienergy/simulate', {
                method: 'POST',
                body: JSON.stringify({
                    tracker: {
                        id: "tracker-01", panel_width: 2.0, panel_length: 4.0, capacity_w: 1000,
                        min_tilt: -60, max_tilt: 60, lat: 43.3, lon: -2.0, parent_parcel_id: "parcel-01"
                    },
                    parcel: { id: "parcel-01", slope: 5.0, aspect: 180.0 },
                    telemetry: { timestamp: new Date().toISOString(), ghi: 800, dni: 600, dhi: 200, actual_tilt: 0, actual_azimuth: 180 },
                    target_tilt: targetTilt
                })
            });
            const data = await res.json();
            setResult(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="nkz-agrienergy space-y-4">
            <SolarParksSection />

            {/* Instant values panel */}
            <Card className="bg-white dark:bg-gray-800 shadow-sm">
                <CardHeader>
                    <CardTitle className="text-sm">{t('agrienergy.panel.title')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    {!selectedEntityId && (
                        <p className="text-xs text-gray-500">{t('agrienergy.panel.selectTracker')}</p>
                    )}
                    {selectedEntityId && statusError && !status && (
                        <p className="text-xs text-amber-600">{t('agrienergy.panel.noData')}</p>
                    )}
                    {selectedEntityId && status && (
                        <>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                    <span className="text-gray-500 block">{t('agrienergy.panel.orientation')}</span>
                                    <span className="font-mono">
                                        {t('agrienergy.panel.tilt')}: {status.orientation.tilt.toFixed(1)}{t('agrienergy.panel.deg')}
                                        {' · '}
                                        {t('agrienergy.panel.azimuth')}: {status.orientation.azimuth.toFixed(1)}{t('agrienergy.panel.deg')}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-500 block">{t('agrienergy.panel.power')}</span>
                                    <span className="font-mono">
                                        {status.power.measured_w != null && (
                                            <>{t('agrienergy.panel.measuredPower')}: {status.power.measured_w.toFixed(0)} {t('agrienergy.panel.W')}</>
                                        )}
                                        {status.power.measured_w != null && status.power.expected_w != null && ' · '}
                                        {status.power.expected_w != null && (
                                            <>{t('agrienergy.panel.expectedPower')}: {status.power.expected_w.toFixed(0)} {t('agrienergy.panel.W')}</>
                                        )}
                                        {status.power.measured_w == null && status.power.expected_w == null && t('agrienergy.panel.noData')}
                                    </span>
                                </div>
                            </div>
                            {Object.keys(status.sensors).length > 0 && (
                                <div className="text-xs">
                                    <span className="text-gray-500 block">{t('agrienergy.panel.sensors')}</span>
                                    <span className="font-mono">
                                        {Object.entries(status.sensors).map(([k, v]) => {
                                            const label = t(`agrienergy.sensorLabels.${k}` as any) || k;
                                            const val = v != null && Number.isFinite(v) ? String(v) : '—';
                                            return `${label}: ${val}`;
                                        }).join(', ')}
                                    </span>
                                </div>
                            )}
                            {selectedEntityId && Object.keys(status.sensors).length === 0 && (
                                <p className="text-xs text-gray-500">{t('agrienergy.signals.configureHint')}</p>
                            )}
                            <p className="text-[10px] text-gray-400">
                                {t('agrienergy.panel.lastUpdate')}: {status.timestamp ? new Date(status.timestamp).toLocaleTimeString() : '—'}
                            </p>
                        </>
                    )}
                </CardContent>
            </Card>

            {selectedEntityId && (
                <AlgorithmSelector
                    trackerId={selectedEntityId}
                    currentAlgorithmId={status?.active_algorithm_id ?? undefined}
                    onSaved={fetchStatus}
                />
            )}
            {selectedEntityId && (
                <ConfigureSignals
                    trackerId={selectedEntityId}
                    currentMapping={status?.signal_mapping}
                    onSaved={fetchStatus}
                />
            )}

            <Card className="nkz-agrienergy-sandbox bg-white dark:bg-gray-800 shadow-sm">
                <CardHeader>
                    <CardTitle>{t('agrienergy.sandbox.title')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">

                    <div className="flex flex-col space-y-2">
                    <label className="text-sm font-medium">{t('agrienergy.sandbox.targetTiltLabel')}</label>
                    <input
                        type="range"
                        min="-60" max="60"
                        value={targetTilt}
                        onChange={e => setTargetTilt(Number(e.target.value))}
                        className="w-full"
                    />
                    <span className="text-center font-bold text-blue-600">{targetTilt}°</span>
                </div>

                <Button
                    onClick={runSimulation}
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                >
                    {loading ? t('agrienergy.sandbox.simulating') : t('agrienergy.sandbox.runSimulation')}
                </Button>

                {result && (
                    <Alert className="mt-4 bg-gray-50 dark:bg-gray-900 border border-gray-200">
                        <h4 className="font-semibold text-sm mb-2">{t('agrienergy.sandbox.resultsTitle')}</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                                <span className="text-gray-500 block">{t('agrienergy.sandbox.expectedPowerLabel')}</span>
                                <span className="font-bold text-green-600">{result.expected_power_w?.toFixed(1) || 0} {t('agrienergy.panel.W')}</span>
                            </div>
                            <div>
                                <span className="text-gray-500 block">{t('agrienergy.sandbox.shadowAreaLabel')}</span>
                                <span className="font-bold text-purple-600">{result.shadow_area_m2?.toFixed(2) || 0} m²</span>
                            </div>
                        </div>
                    </Alert>
                )}
            </CardContent>
        </Card>
        </div>
    );
};
