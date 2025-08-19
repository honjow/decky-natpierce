export enum ResourceType {
  PLUGIN = "plugin",
  CORE = "core",
}

export interface Config {
  status: boolean,
  controller_port: number,
  autostart: boolean,
  costom_port: boolean,
}
