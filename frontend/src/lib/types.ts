export type ProcessingStatus =
  | "registered"
  | "available"
  | "downloaded"
  | "validated"
  | "error";

export interface DatasetMetadata {
  dataset_id: string;
  name: string;
  mission: string;
  instrument: string;
  product_type: string;
  spatial_resolution: string | null;
  acquisition_date_range: string | null;
  geographic_footprint: string | null;
  crs: string;
  source_url: string;
  data_format: string;
  coverage: string | null;
  processing_status: ProcessingStatus;
  scientific_limitations: string | null;
  description: string;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export interface StatusResponse {
  status: string;
  app: string;
  version: string;
  uptime_seconds: number;
  services: Record<string, string>;
}

export interface MapLayer {
  id: string;
  name: string;
  mission: string;
  type: "shaded_relief" | "elevation_dtm" | "multispectral" | "geology" | "orbital_imagery";
  crs: string;
  enabled: boolean;
  isAvailable: boolean;
  statusNote: string;
}
