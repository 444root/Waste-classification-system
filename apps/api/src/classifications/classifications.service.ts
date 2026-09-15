import {
  BadGatewayException,
  Injectable,
  RequestTimeoutException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { mkdir, unlink, writeFile } from 'node:fs/promises';
import { extname, resolve } from 'node:path';
import { randomUUID } from 'node:crypto';
import { DatabaseService } from '../database/database.service';
import { ClassificationFeedbackDto } from './dto/classification-feedback.dto';

export interface ClassificationResult {
  category: string;
  rawCategory: string;
  confidence: number;
  accepted: boolean;
  secondChoice: string;
  confidenceMargin: number;
  probabilities: Record<string, number>;
  recommendation: string;
  modelVersion: string;
}

@Injectable()
export class ClassificationsService {
  private readonly classifierUrl: string;
  private readonly feedbackDir: string;

  constructor(config: ConfigService, private readonly db: DatabaseService) {
    this.classifierUrl = config.get<string>(
      'CLASSIFIER_URL',
      'http://localhost:8000',
    );
    this.feedbackDir = config.get<string>(
      'FEEDBACK_DIR',
      resolve(process.cwd(), 'data', 'feedback'),
    );
  }

  async classify(file: Express.Multer.File): Promise<ClassificationResult> {
    const form = new FormData();
    form.append(
      'file',
      new Blob([new Uint8Array(file.buffer)], { type: file.mimetype }),
      file.originalname,
    );

    try {
      const response = await fetch(`${this.classifierUrl}/predict`, {
        method: 'POST',
        body: form,
        signal: AbortSignal.timeout(90_000),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new BadGatewayException(
          `Classifier rejected the image: ${detail.slice(0, 200)}`,
        );
      }
      return (await response.json()) as ClassificationResult;
    } catch (error) {
      if (error instanceof BadGatewayException) throw error;
      if (error instanceof DOMException && error.name === 'TimeoutError') {
        throw new RequestTimeoutException('Classification timed out');
      }
      throw new BadGatewayException('Classification service is unavailable');
    }
  }

  async saveFeedback(
    file: Express.Multer.File,
    userId: string,
    dto: ClassificationFeedbackDto,
  ) {
    const confidence = Number(dto.confidence);
    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
      throw new BadGatewayException('Invalid classification confidence');
    }

    const extensionByType: Record<string, string> = {
      'image/jpeg': '.jpg',
      'image/png': '.png',
      'image/webp': '.webp',
      'image/heic': '.heic',
      'image/heif': '.heif',
    };
    const originalExtension = extname(file.originalname).toLowerCase();
    const extension =
      extensionByType[file.mimetype] ??
      (['.heic', '.heif'].includes(originalExtension)
        ? originalExtension
        : '.jpg');
    const id = randomUUID();
    const imageName = `${id}${extension}`;
    const imagePath = resolve(this.feedbackDir, imageName);

    await mkdir(this.feedbackDir, { recursive: true });
    await writeFile(imagePath, file.buffer);
    try {
      const result = await this.db.query<{ created_at: Date }>(
        `INSERT INTO classification_feedback
           (id, user_id, predicted_category, corrected_category, confidence,
            image_path, mime_type, original_name)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING created_at`,
        [
          id,
          userId,
          dto.predictedCategory,
          dto.correctedCategory,
          confidence,
          imageName,
          file.mimetype,
          file.originalname,
        ],
      );
      return {
        id,
        message: 'Feedback saved. Thank you for helping improve the model.',
        createdAt: result.rows[0].created_at,
      };
    } catch (error) {
      await unlink(imagePath).catch(() => undefined);
      throw error;
    }
  }
}
