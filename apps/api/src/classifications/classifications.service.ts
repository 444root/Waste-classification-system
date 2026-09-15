import {
  BadGatewayException,
  Injectable,
  RequestTimeoutException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

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

  constructor(config: ConfigService) {
    this.classifierUrl = config.get<string>(
      'CLASSIFIER_URL',
      'http://localhost:8000',
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
}
