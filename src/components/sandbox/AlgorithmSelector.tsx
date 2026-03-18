/**
 * Algorithm selector: list from GET /algorithms, dropdown to set active algorithm per tracker.
 * Saves via PATCH /api/agrienergy/trackers/{id}/algorithm with { activeAlgorithm: { id } }.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '@nekazari/ui-kit';
import { useTranslation } from '@nekazari/sdk';

function fetchWithAuth(path: string, init?: RequestInit): Promise<Response> {
    return fetch(path, { credentials: 'include', ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } });
}

interface AlgorithmPreset {
    id: string;
    name: string;
    logic: Record<string, unknown>;
}

export const AlgorithmSelector: React.FC<{
    trackerId: string | null;
    currentAlgorithmId?: string | null;
    onSaved?: () => void;
}> = ({ trackerId, currentAlgorithmId, onSaved }) => {
    const { t } = useTranslation();
    const [algorithms, setAlgorithms] = useState<AlgorithmPreset[]>([]);
    const [selectedId, setSelectedId] = useState<string>(currentAlgorithmId ?? '');
    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'ok' | 'error'>('idle');

    useEffect(() => {
        setSelectedId(currentAlgorithmId ?? '');
    }, [currentAlgorithmId]);

    const fetchAlgorithms = useCallback(async () => {
        try {
            const res = await fetchWithAuth('/api/agrienergy/algorithms');
            if (res.ok) {
                const data = await res.json();
                setAlgorithms(data.algorithms || []);
            }
        } catch {
            setAlgorithms([]);
        }
    }, []);

    useEffect(() => {
        fetchAlgorithms();
    }, [fetchAlgorithms]);

    const handleChange = async (algorithmId: string) => {
        if (!trackerId || !algorithmId) return;
        setSelectedId(algorithmId);
        setSaving(true);
        setSaveStatus('idle');
        try {
            const res = await fetchWithAuth(
                `/api/agrienergy/trackers/${encodeURIComponent(trackerId)}/algorithm`,
                {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ activeAlgorithm: { id: algorithmId } }),
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

    if (!trackerId) return null;

    return (
        <Card className="bg-white dark:bg-gray-800 shadow-sm">
            <div className="px-4 pt-4">
                <div className="text-sm font-semibold">{t('agrienergy.algorithms.title')}</div>
            </div>
            <div className="p-4 space-y-2">
                <p className="text-xs text-gray-500">{t('agrienergy.algorithms.description')}</p>
                <select
                    className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm"
                    value={selectedId}
                    onChange={(e) => handleChange(e.target.value)}
                    disabled={saving || algorithms.length === 0}
                >
                    <option value="">{t('agrienergy.algorithms.select')}</option>
                    {algorithms.map((a) => (
                        <option key={a.id} value={a.id}>
                            {a.name}
                        </option>
                    ))}
                </select>
                {saveStatus === 'ok' && (
                    <p className="text-xs text-green-600">{t('agrienergy.algorithms.saved')}</p>
                )}
                {saveStatus === 'error' && (
                    <p className="text-xs text-red-600">{t('agrienergy.algorithms.error')}</p>
                )}
            </div>
        </Card>
    );
};
