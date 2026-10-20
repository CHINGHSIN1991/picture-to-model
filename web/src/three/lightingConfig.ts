export interface LightConfig {
  color: string
  intensity: number
  position: [number, number, number]
}

export interface LightingConfig {
  exposure: number
  ambient: { sky: string; ground: string; intensity: number }
  key: LightConfig
  fill: LightConfig
  rim: LightConfig
  shadow: { radius: number; intensity: number }
  environmentIntensity: number
  fog: { enabled: boolean; color: string; near: number; far: number; referenceDistance: number }
  water: { top: string; bottom: string; rayColor: string; rayStrength: number }
  caustics: { strength: number; scale: number; speed: number; animated: boolean }
  material: { roughness: number; metalness: number; coralEmissive: string; coralIntensity: number }
}

// Plain JSON data. Each viewer gets its own copy; GUI changes never mutate defaults.
export const lightingConfig: LightingConfig = {
  exposure: 1,
  ambient: { sky: '#88d6ff', ground: '#396f8c', intensity: 0.85 },
  key: { color: '#fff2d7', intensity: 3.3, position: [3, 5, 2] },
  fill: { color: '#82c8ff', intensity: 1.1, position: [-4, 2, 3] },
  rim: { color: '#66e5ff', intensity: 2.3, position: [1, 3, -4] },
  shadow: { radius: 4, intensity: 0.65 },
  environmentIntensity: 0.12,
  // Near/far at the authored hero distance. Both move with the camera on resize/zoom.
  fog: { enabled: true, color: '#147ab3', near: 5.8, far: 18, referenceDistance: 6.8 },
  water: { top: '#078bd4', bottom: '#043267', rayColor: '#9bedff', rayStrength: 0.035 },
  caustics: { strength: 0.18, scale: 5, speed: 0.35, animated: true },
  material: { roughness: 0.58, metalness: 0, coralEmissive: '#ffd5dc', coralIntensity: 0.05 },
}
