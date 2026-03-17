/**
 * Configure signals: map algorithm context keys to platform entities/attributes.
 * Fetches signal-sources and current tracker signal_mapping; saves via PATCH.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardContent, CardTitle, Button } from '@nekazari/ui-kit';
import { useApi, useTranslation } from '@nekazari/sdk';

const DEFAULT_CONTEXT_KEYS = ['weather.ghi', 'weather.dni', 'weather.dhi', 'weather.temperature'];

interface SignalSourceAttribute {
    name: string;
    last_value?: number;
}

interface SignalSource {
    entity_id: string;
    entity_name: string;
    type: string;
    attributes: SignalSourceAttribute[];
}

interface MappingRow {
    contextKey: string;
    entityId: string;
    attribute: string;
}

interface ConfigureSignalsProps {
    trackerId: string | null;
    currentMapping: MappingRow[] | null | undefined;
    onSaved?: () => void;
}

export const ConfigureSignals: React.FC<ConfigureSignalsProps> = ({
    trackerId,
    currentMapping,
    onSaved,
}) => {
    const { fetchWithAuth } = useApi();
    const { t } = useTranslation();
    const [sources, setSources] = useState<SignalSource[]>([]);
    const [loadingSources, setLoadingSources] = useState(false);
    const [rows, setRows] = useState<MappingRow[]>(() =>
        DEFAULT_CONTEXT_KEYS.map((contextKey) => ({
            contextKey,
            entityId: '',
            attribute: 'value',
        }))
    );
    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'ok' | 'error'>('idle');

    const fetchSources = useCallback(async () => {
        setLoadingSources(true);
        try {
            const res = await fetchWithAuth('/api/agrienergy/signal-sources');
            if (res.ok) {
                const data = await res.json();
                setSources(data.sources || []);
            }
        } catch {
            setSources([]);
        } finally {
            setLoadingSources(false);
        }
    }, [fetchWithAuth]);

    useEffect(() => {
        fetchSources();
    }, [fetchSources]);

    useEffect(() => {
        if (currentMapping && currentMapping.length > 0) {
            const byKey: Record<string, MappingRow> = {};
            currentMapping.forEach((m) => {
                byKey[m.contextKey] = m;
            });
            setRows((prev) =>
                prev.map((r) => byKey[r.contextKey] || r)
            );
        }
    }, [currentMapping]);

    const setRow = (contextKey: string, field: 'entityId' | 'attribute', value: string) => {
        setRows((prev) =>
            prev.map((r) =>
                r.contextKey === contextKey ? { ...r, [field]: value } : r
            )
        );
        setSaveStatus('idle');
    };

    const handleSave = async () => {
        if (!trackerId) return;
        const payload = rows.filter((r) => r.entityId && r.attribute).map((r) => ({
            contextKey: r.contextKey,
            entityId: r.entityId,
            attribute: r.attribute,
        }));
        setSaving(true);
        setSaveStatus('idle');
        try {
            const res = await fetchWithAuth(
                `/api/agrienergy/trackers/${encodeURIComponent(trackerId)}/signal-mapping`,
                {
                    method: 'PATCH',
                    body: JSON.stringify({ signalMapping: payload }),
                }
            );
            if (res.ok) {
                setSaveStatus('ok');
                onSaved?.();
            } else {
                setSaveStatus('error');
            }
        } catch {
            setSaveStatus('error');
        } finally {
            setSaving(false);
        }
    };

    const getLabel = (key: string) =>
        t(`agrienergy.sensorLabels.${key}` as any) || key;

    if (!trackerId) return null;

    return (
        <Card className="bg-white dark:bg-gray-800 shadow-sm">
            <CardHeader>
                <CardTitle className="text-sm">{t('agrienergy.signals.title')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <p className="text-xs text-gray-500">{t('agrienergy.signals.description')}</p>
                {loadingSources && (
                    <p className="text-xs text-gray-400">{t('common.loading')}</p>
                )}
                {!loadingSources && sources.length === 0 && (
                    <p className="text-xs text-amber-600">{t('agrienergy.signals.noSources')}</p>
                )}
                {sources.length > 0 && (
                    <>
                        <div className="space-y-2">
                            {rows.map((row) => (
                                <div
                                    key={row.contextKey}
                                    className="grid grid-cols-1 gap-1 text-xs sm:grid-cols-3"
                                >
                                    <label className="font-medium text-gray-700 dark:text-gray-300">
                                        {getLabel(row.contextKey)}
                                    </label>
                                    <select
                                        className="rounded border border-gray-300 bg-white px-2 py-1 dark:border-gray-600 dark:bg-gray-700"
                                        value={row.entityId}
                                        onChange={(e) => setRow(row.contextKey, 'entityId', e.target.value)}
                                    >
                                        <option value="">{t('agrienergy.signals.selectEntity')}</option>
                                        {sources.map((s) => (
                                            <option key={s.entity_id} value={s.entity_id}>
                                                {s.entity_name} ({s.type})
                                            </option>
                                        ))}
                                    </select>
                                    <select
                                        className="rounded border border-gray-300 bg-white px-2 py-1 dark:border-gray-600 dark:bg-gray-700"
                                        value={row.attribute}
                                        onChange={(e) => setRow(row.contextKey, 'attribute', e.target.value)}
                                        disabled={!row.entityId}
                                    >
                                        <option value="">{t('agrienergy.signals.selectAttribute')}</option>
                                        {sources
                                            .find((s) => s.entity_id === row.entityId)
                                            ?.attributes.map((a) => (
                                                <option key={a.name} value={a.name}>
                                                    {a.name}
                                                    {a.last_value != null ? ` (${a.last_value})` : ''}
                                                </option>
                                            ))}
                                    </select>
                                </div>
                            ))}
                        </div>
                        <Button
                            onClick={handleSave}
                            disabled={saving}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm"
                        >
                            {saving ? t('common.loading') : t('agrienergy.signals.save')}
                        </Button>
                        {saveStatus === 'ok' && (
                            <p className="text-xs text-green-600">{t('agrienergy.signals.saved')}</p>
                        )}
                        {saveStatus === 'error' && (
                            <p className="text-xs text-red-600">{t('agrienergy.signals.error')}</p>
                        )}
                    </>
                )}
            </CardContent>
        </Card>
    );
};
