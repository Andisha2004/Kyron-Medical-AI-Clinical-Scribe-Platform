export interface TemplateSection {
  id: string;
  section: string;
  instructions: string;
  sort_order: number;
}

export interface TemplateSummary {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  sections: TemplateSection[];
}
