import React, { useState } from 'react';
import { Card, CardHeader, CardContent, CardTitle, Button, Alert } from '@nekazari/ui-kit';
import { useApi } from '@nekazari/sdk';

export const AgriEnergySandbox: React.FC = () => {
    const { fetchWithAuth } = useApi();
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [targetTilt, setTargetTilt] = useState<number>(30);

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
        <Card className="nkz-agrienergy-sandbox bg-white dark:bg-gray-800 shadow-sm">
            <CardHeader>
                <CardTitle>AgriEnergy Sandbox (Shadow Mode)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">

                <div className="flex flex-col space-y-2">
                    <label className="text-sm font-medium">Target Tilt Angle (deg)</label>
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
                    {loading ? 'Simulating...' : 'Run Simulation'}
                </Button>

                {result && (
                    <Alert className="mt-4 bg-gray-50 dark:bg-gray-900 border border-gray-200">
                        <h4 className="font-semibold text-sm mb-2">Simulation Results:</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                                <span className="text-gray-500 block">Expected Power</span>
                                <span className="font-bold text-green-600">{result.expected_power_w?.toFixed(1) || 0} W</span>
                            </div>
                            <div>
                                <span className="text-gray-500 block">Shadow Area (2.5D)</span>
                                <span className="font-bold text-purple-600">{result.shadow_area_m2?.toFixed(2) || 0} m²</span>
                            </div>
                        </div>
                    </Alert>
                )}
            </CardContent>
        </Card>
    );
};
