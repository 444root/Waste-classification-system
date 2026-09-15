import { IsIn, IsNumberString, IsString } from 'class-validator';

const CATEGORIES = [
  'glass',
  'metal',
  'general_trash',
  'organic',
  'paper',
  'plastic',
  'other',
] as const;

export class ClassificationFeedbackDto {
  @IsString()
  @IsIn(CATEGORIES)
  predictedCategory: string;

  @IsString()
  @IsIn(CATEGORIES)
  correctedCategory: string;

  @IsNumberString()
  confidence: string;
}
