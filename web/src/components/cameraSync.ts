// 比較模式用的共享相機狀態:由滑鼠所在的 pane 發布,另一側跟隨
export interface CameraSync {
  active: string | null
  pos: [number, number, number]
  target: [number, number, number]
}

export function createCameraSync(): CameraSync {
  return { active: null, pos: [2.2, 1.4, 2.2], target: [0, 0, 0] }
}
