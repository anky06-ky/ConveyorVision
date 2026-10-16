from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

SRC = next(Path(r'D:\Nhu\BT_03').glob('*01.docx'))
OUT = Path(r'D:\Nhu\BT_03\Bai_tap_nhom_5_trinh_bay_theo_mau.docx')

# Ten report pages: source content is reorganized and duplicate statements are
# consolidated; practical examples remain explicitly illustrative.
PAGES = [
('PHẦN MỞ ĐẦU', [
('1. Lý do chọn đề tài', [
'Sàn giao dịch bất động sản (BĐS) có thể kết nối người có nhu cầu mua, bán, thuê và cho thuê; đồng thời tập trung thông tin, hỗ trợ khách hàng tìm kiếm, đàm phán và thực hiện giao dịch. Do giá trị tài sản thường lớn, hồ sơ có nhiều thành phần và quyền lợi của các bên gắn với nhau, việc công khai thông tin và kiểm tra điều kiện giao dịch có ý nghĩa thiết thực đối với sự an toàn của thị trường.',
'Trong thực tiễn, khách hàng có thể gặp rủi ro khi thông tin quảng cáo khác với hồ sơ, tin đăng chưa được cập nhật, phí dịch vụ chưa rõ hoặc vai trò của sàn và người môi giới bị nhầm lẫn. Giao dịch qua website còn đặt ra yêu cầu về xác thực người đăng, lưu giữ nội dung và chứng cứ điện tử. Vì vậy, nghiên cứu quy định hiện hành và cách áp dụng vào hoạt động của sàn giúp nhận diện đúng quyền, nghĩa vụ và giới hạn trách nhiệm của từng chủ thể.'
]),
('2. Mục tiêu và nhiệm vụ nghiên cứu', [
'Báo cáo hướng đến việc hệ thống hóa cơ sở lý luận và quy định pháp luật về kinh doanh dịch vụ sàn giao dịch BĐS; phân tích những vấn đề phát sinh trong quá trình cung cấp thông tin, môi giới, thu phí, giao dịch trực tuyến và giám sát; từ đó đề xuất giải pháp hoàn thiện pháp luật và nâng cao hiệu quả thi hành.',
'Các nhiệm vụ gồm: làm rõ khái niệm, đặc điểm, chức năng và vai trò của sàn; phân tích điều kiện thành lập, hoạt động, quyền và nghĩa vụ của sàn cùng yêu cầu đối với người môi giới; xem xét các rủi ro thực tiễn về thông tin, trách nhiệm, phí dịch vụ và quản lý; đề xuất giải pháp cho cơ quan quản lý, doanh nghiệp và khách hàng.'
]),
('3. Đối tượng, phạm vi và phương pháp', [
'Đối tượng nghiên cứu là các quy định về sàn giao dịch BĐS và quan hệ giữa sàn, doanh nghiệp kinh doanh dịch vụ, người môi giới và khách hàng. Phạm vi tập trung vào pháp luật Việt Nam về dịch vụ sàn, chủ yếu là Luật Kinh doanh bất động sản năm 2023 và các văn bản hướng dẫn, sửa đổi được liệt kê ở cuối báo cáo; có đối chiếu với pháp luật dân sự và giao dịch điện tử khi cần thiết. Báo cáo không đi sâu vào hoạt động đầu tư dự án hoặc tranh chấp quyền sử dụng đất thuần túy.',
'Phương pháp gồm phân tích quy phạm, tổng hợp, so sánh và tình huống minh họa. Tài liệu Word gốc không kèm bộ số liệu khảo sát hoặc hồ sơ vụ án cụ thể, vì vậy các tình huống được nêu để minh họa vấn đề pháp lý, không được trình bày như sự kiện đã xảy ra hay kết quả khảo sát trên phạm vi cả nước.'
])]),
('CHƯƠNG I. CƠ SỞ LÝ LUẬN VÀ PHÁP LUẬT HIỆN HÀNH', [
('1.1. Khái niệm, bản chất và vai trò của sàn giao dịch', [
'Khoản 10 Điều 3 Luật Kinh doanh bất động sản năm 2023 xác định sàn giao dịch BĐS là nơi diễn ra các giao dịch mua bán, chuyển nhượng, cho thuê, cho thuê lại, cho thuê mua BĐS được thành lập và hoạt động theo Luật. Sàn là tổ chức kinh doanh dịch vụ, thực hiện công việc theo quy trình và hợp đồng với khách hàng; sàn không mặc nhiên trở thành chủ sở hữu, bên bán hoặc người bảo đảm mọi thông tin do bên khác cung cấp.',
'Vai trò trung gian thể hiện ở việc kiểm tra hồ sơ và điều kiện đưa BĐS vào kinh doanh, niêm yết thông tin, hỗ trợ khách hàng lựa chọn, đàm phán, lập hợp đồng và lưu giữ hồ sơ giao dịch. Dịch vụ này có thể giảm chi phí tìm kiếm thông tin và giúp các bên ghi nhận rõ hơn quá trình làm việc. Hiệu quả đó phụ thuộc vào chất lượng kiểm tra, tính trung thực của thông tin và việc tuân thủ trách nhiệm của sàn.'
]),
('1.2. Cơ sở pháp lý và định hướng điều chỉnh', [
'Cơ sở trực tiếp là Luật Kinh doanh bất động sản số 29/2023/QH15, được sửa đổi về thời điểm có hiệu lực tại Luật số 43/2024/QH15, cùng Nghị định số 96/2024/NĐ-CP quy định chi tiết một số điều của Luật. Các văn bản có liên quan trong tài liệu nghiên cứu gồm Nghị định số 54/2026/NĐ-CP về sửa đổi quy định trong lĩnh vực nhà ở, kinh doanh BĐS; Nghị định số 357/2025/NĐ-CP về hệ thống thông tin, cơ sở dữ liệu nhà ở và thị trường BĐS; và Nghị định số 339/2026/NĐ-CP về xử phạt vi phạm hành chính trong lĩnh vực này.',
'Điều 7 Luật năm 2023 thể hiện chính sách khuyến khích tổ chức, cá nhân giao dịch thông qua sàn. Cùng với đó, Luật đặt ra chuẩn mực đối với việc thành lập, cấp phép, kiểm tra hồ sơ, cung cấp thông tin và lưu trữ giao dịch. Khi sàn giao dịch điện tử, hoạt động còn phải tuân thủ Luật Giao dịch điện tử và quy định có liên quan. Các nghĩa vụ cụ thể cần được xác định theo loại dịch vụ, hợp đồng và vai trò thực tế của từng chủ thể.'
])]),
('CHƯƠNG I. CƠ SỞ LÝ LUẬN VÀ PHÁP LUẬT HIỆN HÀNH', [
('1.3. Điều kiện thành lập và hoạt động của sàn', [
'Theo Điều 54 Luật Kinh doanh bất động sản năm 2023, tổ chức, cá nhân kinh doanh dịch vụ sàn phải thành lập doanh nghiệp kinh doanh dịch vụ BĐS. Tên doanh nghiệp phải có cụm từ “sàn giao dịch bất động sản” và không được trùng hoặc gây nhầm lẫn với tên đã đăng ký. Trước khi hoạt động, sàn gửi hồ sơ đến cơ quan quản lý nhà nước về kinh doanh BĐS cấp tỉnh nơi đặt trụ sở chính để được cấp giấy phép hoạt động.',
'Điều 55 yêu cầu người quản lý, điều hành sàn có quyền quản lý doanh nghiệp tại Việt Nam và hoàn thành khóa đào tạo quản lý, điều hành sàn. Sàn phải đăng ký địa điểm hoạt động cố định, có cơ sở vật chất và kỹ thuật phù hợp, đồng thời ban hành và công khai quy trình giao dịch. Nghị định số 96/2024/NĐ-CP hướng dẫn hồ sơ, trình tự và một số điều kiện chi tiết; khi áp dụng cần đối chiếu văn bản sửa đổi còn hiệu lực.'
]),
('1.4. Điều kiện đối với hoạt động môi giới trong sàn', [
'Sàn có thể cung cấp dịch vụ môi giới, nhưng hoạt động này phải tuân thủ các quy định riêng tại Mục 2 Chương VII của Luật. Doanh nghiệp kinh doanh dịch vụ môi giới phải đáp ứng điều kiện về quy chế, cơ sở vật chất và nhân sự có chứng chỉ; cá nhân hành nghề phải có chứng chỉ môi giới và làm việc trong doanh nghiệp kinh doanh dịch vụ sàn hoặc doanh nghiệp môi giới đủ điều kiện. Vì vậy, cần phân biệt điều kiện hoạt động của sàn với điều kiện của doanh nghiệp và cá nhân khi thực hiện môi giới.',
'Người môi giới cần cung cấp thông tin trung thực, làm rõ phạm vi công việc và khoản thù lao, hoa hồng theo thỏa thuận. Đào tạo, bồi dưỡng thường xuyên và việc sàn quản lý nhân viên là một phần của trách nhiệm nghề nghiệp. Khi phát sinh sai lệch, cần xem xét ai cung cấp thông tin, sàn đã kiểm tra và công bố ra sao, hợp đồng dịch vụ quy định thế nào và thiệt hại có quan hệ với hành vi của chủ thể nào.'
])]),
('CHƯƠNG I. CƠ SỞ LÝ LUẬN VÀ PHÁP LUẬT HIỆN HÀNH', [
('1.5. Nội dung hoạt động, quyền và nghĩa vụ của sàn', [
'Điều 56 Luật Kinh doanh bất động sản năm 2023 quy định sàn kiểm tra tính pháp lý và điều kiện đưa BĐS vào kinh doanh; niêm yết, cung cấp thông tin đủ điều kiện; hỗ trợ khách hàng tìm kiếm, lựa chọn; thực hiện môi giới, hỗ trợ đàm phán và lập, ký hợp đồng; hỗ trợ thanh toán, bàn giao giấy tờ, lưu trữ hồ sơ và xác nhận giao dịch. Sàn còn cung cấp thông tin giao dịch cho cơ quan quản lý cấp tỉnh theo quy định.',
'Sàn có quyền yêu cầu khách hàng cung cấp hồ sơ, từ chối BĐS không đủ điều kiện và thu phí dịch vụ theo thỏa thuận (Điều 57). Nghĩa vụ gồm bảo đảm BĐS đưa lên sàn đủ điều kiện, niêm yết và cung cấp hồ sơ trung thực, chịu trách nhiệm về thông tin do mình cung cấp, duy trì điều kiện hoạt động, báo cáo, nộp thuế, bồi thường thiệt hại do lỗi, quản lý và đào tạo nhân viên, lưu trữ hồ sơ (Điều 58). Khách hàng có quyền yêu cầu sàn cung cấp thông tin và yêu cầu bồi thường nếu có căn cứ về lỗi và thiệt hại.'
]),
('1.6. Hợp đồng dịch vụ và thanh toán', [
'Hợp đồng kinh doanh dịch vụ BĐS cần ghi rõ chủ thể, đối tượng và nội dung dịch vụ, yêu cầu và kết quả, thời hạn, phí hoặc hoa hồng, phương thức và thời hạn thanh toán, quyền và nghĩa vụ, giải quyết tranh chấp và thời điểm có hiệu lực. Ghi đầy đủ các điều khoản này giúp xác định khi nào phí phát sinh, bên nào phải trả và công việc nào đã được thực hiện.',
'Khoản 2 Điều 48 Luật năm 2023 quy định doanh nghiệp kinh doanh dịch vụ BĐS nhận tiền thanh toán theo hợp đồng dịch vụ từ khách hàng thông qua tài khoản mở tại tổ chức tín dụng hoạt động hợp pháp tại Việt Nam. Quy định này cần được trình bày đúng phạm vi: đây là phương thức nhận tiền của doanh nghiệp theo hợp đồng, không đồng nghĩa mọi khoản tiền giữa mọi bên trong mọi giao dịch phải chuyển qua sàn.'
])]),
('CHƯƠNG II. THỰC TIỄN ÁP DỤNG VÀ NHỮNG VẤN ĐỀ PHÁT SINH', [
('2.1. Công khai và kiểm tra thông tin bất động sản', [
'Thông tin là cơ sở để khách hàng đánh giá BĐS và quyết định giao dịch. Điều 6 Luật Kinh doanh bất động sản năm 2023 quy định việc công khai thông tin về BĐS, dự án trước khi đưa vào kinh doanh và yêu cầu cập nhật khi có thay đổi. Điều 56 đồng thời giao sàn nhiệm vụ kiểm tra điều kiện, niêm yết và cung cấp thông tin. Tùy loại tài sản, việc rà soát có thể liên quan đến giấy tờ quyền, vị trí, quy mô, tiến độ, tình trạng hạn chế quyền, thế chấp và tài liệu về điều kiện kinh doanh.',
'Một tình huống minh họa là bên bán gửi hồ sơ ban đầu cho sàn nhưng sau đó tình trạng thế chấp hoặc điều kiện giao dịch thay đổi mà tin đăng chưa cập nhật. Khách hàng chỉ nhìn thấy nội dung quảng cáo và hiểu đó là thông tin mới nhất. Tình huống này cho thấy cần ghi nhận nguồn hồ sơ, ngày kiểm tra, nội dung đã công bố và lần cập nhật gần nhất; nếu tài liệu chưa đủ để xác minh, sàn cần nêu rõ phần chưa xác nhận thay vì trình bày như một dữ kiện chắc chắn.',
'Khách hàng cũng cần được tiếp cận hồ sơ liên quan trước khi đặt cọc hoặc thanh toán. Sàn nên phân biệt rõ tài liệu do bên bán cung cấp với nội dung đã được đối chiếu, hướng dẫn khách kiểm tra vấn đề vượt quá phạm vi dịch vụ và không dùng tên gọi “sàn” như một sự bảo đảm thay cho việc đọc hợp đồng, hồ sơ pháp lý.'
])]),
('CHƯƠNG II. THỰC TIỄN ÁP DỤNG VÀ NHỮNG VẤN ĐỀ PHÁT SINH', [
('2.2. Quảng cáo, thông tin về giá và nguy cơ gây hiểu nhầm', [
'Nguồn Word gốc nêu các nguy cơ như nhận định về khả năng tăng giá, thông tin khan hiếm hoặc số lượng giao dịch không có căn cứ kiểm chứng. Những biểu hiện này cần được xem xét thận trọng: nhận định thị trường hoặc quảng cáo thông thường không tự động là hành vi vi phạm; việc đánh giá phải dựa trên nội dung cụ thể, tài liệu chứng minh, mục đích cung cấp và ảnh hưởng đến quyết định của khách hàng.',
'Tình huống minh họa: nhân viên môi giới khẳng định một căn nhà “đầy đủ giấy tờ” và “sắp tăng giá” để thúc đẩy khách đặt cọc, trong khi chưa đối chiếu hồ sơ hoặc không có căn cứ cho dự báo. Nếu phát sinh tranh chấp, các bên cần lưu tin nhắn, nội dung quảng cáo, tài liệu được cung cấp, hợp đồng, chứng từ thanh toán và diễn biến xử lý. Chỉ sau khi xác định hành vi, lỗi, thiệt hại và quan hệ nhân quả mới có cơ sở xem xét trách nhiệm theo hợp đồng và pháp luật.',
'Cách phân tích này giúp tránh quy kết chung cho mọi người môi giới hoặc mọi sàn. Sàn có nghĩa vụ quản lý nhân viên, kiểm tra và chịu trách nhiệm về thông tin do mình niêm yết, cung cấp; cá nhân môi giới và bên có tài sản cũng có nghĩa vụ tương ứng theo vai trò, hợp đồng và hành vi của mình.'
]),
('2.3. Tranh chấp phí dịch vụ và trách nhiệm của các bên', [
'Tranh chấp phí có thể phát sinh khi hợp đồng không xác định rõ khoản phí, thời điểm phát sinh nghĩa vụ, điều kiện được hưởng hoa hồng hoặc phạm vi công việc. Chẳng hạn, khách hàng cho rằng chỉ trả phí sau khi ký hợp đồng mua bán, trong khi sàn cho rằng đã hoàn thành việc giới thiệu khách hàng theo thỏa thuận. Nếu phí, kết quả dịch vụ và chứng cứ thực hiện không được ghi rõ, mỗi bên có thể hiểu khác nhau.',
'Khi BĐS không đủ điều kiện giao dịch, trách nhiệm cũng không mặc nhiên thuộc riêng một chủ thể. Cần xem xét ai có quyền đưa tài sản ra giao dịch, bên nào cung cấp hồ sơ, sàn đã thực hiện nghĩa vụ kiểm tra và công khai thế nào, môi giới đã nói gì, khách hàng dựa vào thông tin nào và thiệt hại thực tế ra sao. Luật quy định sàn bồi thường thiệt hại do lỗi của mình, nhưng việc xác định lỗi và mức bồi thường đòi hỏi chứng cứ cụ thể.'
])]),
('CHƯƠNG II. THỰC TIỄN ÁP DỤNG VÀ NHỮNG VẤN ĐỀ PHÁT SINH', [
('2.4. Sàn trực tuyến và chứng cứ giao dịch', [
'Website và nền tảng trực tuyến giúp khách hàng tìm kiếm thông tin nhanh, nhưng đồng thời làm phát sinh rủi ro về danh tính người đăng, quyền đưa BĐS ra giao dịch, độ chính xác của hình ảnh và giá, cũng như tin đã hết hiệu lực. Một trang đăng tin không đương nhiên là sàn giao dịch theo Luật; cần căn cứ mô hình tổ chức, dịch vụ thực tế và điều kiện hoạt động để xác định nghĩa vụ pháp lý tương ứng.',
'Với giao dịch điện tử, các bên cần lưu lại thời điểm đăng, nội dung từng phiên bản, người sửa tin, tài liệu đính kèm, xác nhận của khách hàng và chứng từ thanh toán. Việc sửa hoặc xóa nội dung mà không giữ lịch sử có thể gây khó khăn khi xác định thông tin đã được nhìn thấy lúc nào và ai chịu trách nhiệm. Quy trình quản lý cần bảo vệ dữ liệu cá nhân và chỉ sử dụng thông tin khách hàng đúng mục đích đã thông báo.',
'Nếu phát sinh khiếu nại, khách hàng nên lưu bản chụp màn hình kèm thời gian, thư điện tử, tin nhắn, hợp đồng, giấy biên nhận và yêu cầu giải thích bằng văn bản. Đây là những nguồn có thể hỗ trợ xác định nội dung trao đổi, nhưng giá trị chứng minh phải được xem xét theo pháp luật và toàn bộ bối cảnh vụ việc.'
]),
('2.5. Giám sát, xử lý vi phạm và khó khăn khi áp dụng', [
'Một giao dịch có thể liên quan đến chủ đầu tư, chủ sở hữu, sàn, doanh nghiệp môi giới và cá nhân môi giới. Hồ sơ nằm ở nhiều chủ thể, còn nội dung trên nền tảng có thể được cập nhật liên tục. Vì vậy, cơ quan quản lý và các bên có thể gặp khó khăn khi khôi phục thông tin cũ, phân định hành vi, xác định chứng cứ và áp dụng đúng trách nhiệm. Luật giao cơ quan cấp tỉnh nhiệm vụ quản lý, giám sát, kiểm tra và xử lý theo thẩm quyền.',
'Việc áp dụng pháp luật còn đòi hỏi đối chiếu quy định về kinh doanh BĐS với đất đai, nhà ở, xây dựng, dân sự và giao dịch điện tử. Sàn không phải lúc nào cũng có quyền tự xác nhận mọi vấn đề thuộc hồ sơ của cơ quan khác; khách hàng cũng có thể thiếu khả năng tự đọc tài liệu. Do đó, cần phân biệt rõ điều sàn có nghĩa vụ kiểm tra, điều cần yêu cầu bên có tài sản cung cấp và điều cần xác minh tại cơ quan có thẩm quyền.',
'Tài liệu nguồn chưa có báo cáo thanh tra, số liệu khảo sát doanh nghiệp hay bản án cụ thể để đo mức độ phổ biến của các vấn đề nêu trên. Vì vậy, các nhận định ở phần này được trình bày như những rủi ro và vướng mắc cần quan tâm, không kết luận rằng mọi sàn đều vi phạm hoặc các hiện tượng xảy ra ở một tỷ lệ nhất định.'
])]),
('CHƯƠNG III. KIẾN NGHỊ HOÀN THIỆN VÀ NÂNG CAO HIỆU QUẢ THI HÀNH', [
('3.1. Nhóm giải pháp hoàn thiện thể chế và quy trình pháp lý', [
'Thứ nhất, cần tiếp tục hướng dẫn rõ quy trình rà soát hồ sơ theo từng loại BĐS, tiêu chí xác định “đã kiểm tra” và cách ghi nhận nội dung chưa thể xác minh. Hướng dẫn nên phân biệt nghĩa vụ của bên bán hoặc chủ đầu tư trong việc cung cấp hồ sơ với nghĩa vụ của sàn trong kiểm tra điều kiện, niêm yết và cung cấp thông tin; tránh tạo cảm giác rằng sàn có thể thay cơ quan nhà nước xác nhận mọi dữ liệu.',
'Thứ hai, cần làm rõ cách xác định trách nhiệm khi thông tin sai lệch được cung cấp bởi một chủ thể nhưng được sàn tiếp tục đăng tải hoặc môi giới sử dụng. Việc xem xét nên dựa trên hành vi, nghĩa vụ, lỗi, thiệt hại và quan hệ nhân quả, đồng thời bảo đảm quyền yêu cầu bồi thường theo quy định. Hợp đồng dịch vụ cần nêu rõ đầu việc, giới hạn dịch vụ, phí, thời điểm thanh toán, cách sửa đổi thông tin và phương thức giải quyết khiếu nại.',
'Thứ ba, cần rà soát tính thống nhất giữa quy định về kinh doanh BĐS với đất đai, nhà ở, xây dựng, dân sự và giao dịch điện tử. Việc sửa đổi, bổ sung nên dựa trên tổng kết thi hành, phản ánh của doanh nghiệp, quyết định xử lý vi phạm và bản án có liên quan; không nên đặt ra nghĩa vụ mới nếu chưa có căn cứ đánh giá tác động và nguồn lực thực hiện.'
]),
('3.2. Nhóm giải pháp về tổ chức thực hiện và bảo vệ khách hàng', [
'Đối với sàn, nên chuẩn hóa quy trình tiếp nhận và phân loại hồ sơ; lập danh mục tài liệu phải kiểm tra theo từng loại BĐS; lưu ngày nhận, nguồn cung cấp, người kiểm tra, kết quả đối chiếu và lịch sử cập nhật tin. Trước khi quảng cáo, cần rà soát nội dung về giá, tình trạng pháp lý, tiến độ và quyền giao dịch; thông tin chưa xác nhận phải được chú thích rõ. Nhân viên cần được đào tạo định kỳ và chịu sự giám sát của người quản lý.',
'Đối với cơ quan quản lý, cần công khai hướng dẫn thủ tục, cập nhật dữ liệu trong hệ thống thông tin, duy trì kiểm tra theo thẩm quyền và tiếp nhận phản ánh có chứng cứ. Việc phối hợp giữa cơ quan quản lý kinh doanh BĐS và cơ quan phụ trách dữ liệu đất đai, nhà ở, xây dựng có thể giúp việc tra cứu thuận tiện hơn; kết nối dữ liệu cần đi cùng yêu cầu về chất lượng, cập nhật và bảo vệ thông tin.',
'Đối với khách hàng, cần đọc hợp đồng dịch vụ và hợp đồng giao dịch, yêu cầu hồ sơ trước khi đặt cọc, kiểm tra lại thông tin quan trọng và giữ chứng từ trao đổi, thanh toán. Không nên quyết định chỉ dựa vào lời hứa về lợi nhuận hoặc khả năng tăng giá. Các biện pháp này không thay thế trách nhiệm pháp lý của sàn, nhưng giúp khách hàng nhận biết rủi ro và có căn cứ khi cần khiếu nại.'
])]),
]

CONCLUSION = [
'Sàn giao dịch BĐS có vai trò trung gian trong việc cung cấp thông tin, hỗ trợ giao dịch và lưu trữ hồ sơ. Luật Kinh doanh bất động sản năm 2023 quy định điều kiện thành lập, hoạt động, nội dung dịch vụ, quyền và nghĩa vụ của sàn; đồng thời yêu cầu trách nhiệm về thông tin, hồ sơ, nhân viên và thiệt hại do lỗi của sàn. Việc thực hiện các quy định này cần gắn với hợp đồng rõ ràng, quy trình kiểm tra có thể truy xuất và sự phối hợp của các chủ thể liên quan.',
'Các vấn đề về thông tin chưa cập nhật, quảng cáo thiếu căn cứ, tranh chấp phí, giao dịch trực tuyến và phân định trách nhiệm cần được đánh giá dựa trên tài liệu của từng vụ việc. Do nguồn nghiên cứu chưa có số liệu khảo sát hay bản án cụ thể, báo cáo không khẳng định mức độ phổ biến của các hiện tượng. Giải pháp phù hợp là hoàn thiện hướng dẫn, chuẩn hóa lưu trữ và kiểm tra, tăng khả năng tiếp cận dữ liệu, nâng cao giám sát và giúp khách hàng hiểu rõ hồ sơ, hợp đồng trước khi giao dịch.'
]
REFERENCES = [
'Quốc hội (2023), Luật Kinh doanh bất động sản số 29/2023/QH15; Luật số 43/2024/QH15 sửa đổi thời điểm có hiệu lực.',
'Chính phủ (2024), Nghị định số 96/2024/NĐ-CP quy định chi tiết một số điều của Luật Kinh doanh bất động sản.',
'Chính phủ (2026), Nghị định số 54/2026/NĐ-CP sửa đổi, bổ sung một số nghị định trong lĩnh vực nhà ở, kinh doanh bất động sản.',
'Chính phủ (2025), Nghị định số 357/2025/NĐ-CP về xây dựng và quản lý hệ thống thông tin, cơ sở dữ liệu về nhà ở và thị trường bất động sản.',
'Chính phủ (2026), Nghị định số 339/2026/NĐ-CP quy định xử phạt vi phạm hành chính trong lĩnh vực xây dựng, nhà ở và kinh doanh bất động sản.',
'Quốc hội (2015), Bộ luật Dân sự số 91/2015/QH13.',
'Quốc hội (2023), Luật Giao dịch điện tử số 20/2023/QH15.'
]
TOC = [
(0,'PHẦN MỞ ĐẦU','1'), (1,'1. Lý do chọn đề tài','1'), (1,'2. Mục tiêu và nhiệm vụ nghiên cứu','1'), (1,'3. Đối tượng, phạm vi và phương pháp','1'),
(0,'CHƯƠNG I. CƠ SỞ LÝ LUẬN VÀ PHÁP LUẬT HIỆN HÀNH','2'), (1,'1.1. Khái niệm, bản chất và vai trò của sàn giao dịch','2'), (1,'1.2. Cơ sở pháp lý và định hướng điều chỉnh','2'), (1,'1.3. Điều kiện thành lập và hoạt động của sàn','3'), (1,'1.4. Điều kiện đối với hoạt động môi giới trong sàn','3'), (1,'1.5. Nội dung hoạt động, quyền và nghĩa vụ của sàn','4'), (1,'1.6. Hợp đồng dịch vụ và thanh toán','4'),
(0,'CHƯƠNG II. THỰC TIỄN ÁP DỤNG VÀ NHỮNG VẤN ĐỀ PHÁT SINH','5'), (1,'2.1. Công khai và kiểm tra thông tin bất động sản','5'), (1,'2.2. Quảng cáo, thông tin về giá và nguy cơ gây hiểu nhầm','6'), (1,'2.3. Tranh chấp phí dịch vụ và trách nhiệm của các bên','6'), (1,'2.4. Sàn trực tuyến và chứng cứ giao dịch','7'), (1,'2.5. Giám sát và khó khăn khi áp dụng pháp luật','8'),
(0,'CHƯƠNG III. KIẾN NGHỊ HOÀN THIỆN VÀ NÂNG CAO HIỆU QUẢ THI HÀNH','9'), (1,'3.1. Hoàn thiện thể chế và quy trình pháp lý','9'), (1,'3.2. Tổ chức thực hiện và bảo vệ khách hàng','9'), (0,'KẾT LUẬN VÀ DANH MỤC TÀI LIỆU THAM KHẢO','10')]

def set_font(run, size=13, bold=None, italic=None):
    run.font.name = 'Times New Roman'
    rpr = run._element.get_or_add_rPr()
    for key in ('ascii','hAnsi','eastAsia'):
        rpr.rFonts.set(qn('w:'+key), 'Times New Roman')
    run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic

def set_margins(sec):
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3.5), Cm(2)
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.5)
    sec.header_distance, sec.footer_distance = Cm(1.25), Cm(1.25)

def set_numbering(sec, fmt, start):
    el = sec._sectPr.find(qn('w:pgNumType'))
    if el is None:
        el = OxmlElement('w:pgNumType'); sec._sectPr.append(el)
    el.set(qn('w:fmt'), fmt); el.set(qn('w:start'), str(start))

def clear_p(p):
    for el in list(p._p):
        if el.tag != qn('w:pPr'): p._p.remove(el)

def add_field(p, code, fallback):
    for kind, value in [('begin',None),('instr',code),('separate',None),('text',fallback),('end',None)]:
        r = OxmlElement('w:r')
        if kind in ('begin','separate','end'):
            fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), kind); r.append(fc)
        elif kind == 'instr':
            it = OxmlElement('w:instrText'); it.set(qn('xml:space'),'preserve'); it.text = f' {value} '; r.append(it)
        else:
            t = OxmlElement('w:t'); t.text = value; r.append(t)
        p._p.append(r)
    for run in p.runs: set_font(run,11)

def cell_margins(cell, v=70):
    tcpr=cell._tc.get_or_add_tcPr(); mar=OxmlElement('w:tcMar')
    for side in ('top','start','bottom','end'):
        e=OxmlElement('w:'+side); e.set(qn('w:w'),str(v)); e.set(qn('w:type'),'dxa'); mar.append(e)
    tcpr.append(mar)

def borders(table, toc=False):
    pr=table._tbl.tblPr; b=OxmlElement('w:tblBorders')
    for side in ('top','left','bottom','right','insideH','insideV'):
        e=OxmlElement('w:'+side)
        if toc and side in ('top','left','bottom','right','insideV'):
            e.set(qn('w:val'),'nil')
        else:
            e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'3' if toc else '5'); e.set(qn('w:color'),'D9D9D9' if toc else '000000')
        b.append(e)
    pr.append(b)

def add_heading(doc, text, level=2, center=False):
    p=doc.add_paragraph(); p.style='Heading 1' if level==1 else 'Heading 2'
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER if (level==1 or center) else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_before=Pt(1 if level==2 else 0)
    p.paragraph_format.space_after=Pt(4 if level==2 else 7); p.paragraph_format.line_spacing=1.1; p.paragraph_format.keep_with_next=True
    set_font(p.add_run(text),16 if level==1 else 13,True); return p

def add_body(doc, text):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent=Cm(.65); p.paragraph_format.space_after=Pt(4)
    p.paragraph_format.line_spacing=1.3; p.paragraph_format.keep_together=True; p.paragraph_format.widow_control=True
    set_font(p.add_run(text),13); return p

def add_center(doc, text, size=13, after=5, bold=True, italic=False):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(after); p.paragraph_format.line_spacing=1.12
    set_font(p.add_run(text),size,bold,italic); return p

def create():
    src=Document(SRC); d=Document(); s1=d.sections[0]; set_margins(s1)
    s1.different_first_page_header_footer=True; clear_p(s1.footer.paragraphs[0]); clear_p(s1.first_page_footer.paragraphs[0])
    normal=d.styles['Normal']; normal.font.name='Times New Roman'; normal.font.size=Pt(13); normal.paragraph_format.line_spacing=1.3
    for key in ('ascii','hAnsi','eastAsia'): normal._element.rPr.rFonts.set(qn('w:'+key),'Times New Roman')
    for nm,sz in [('Heading 1',16),('Heading 2',13)]:
        st=d.styles[nm]; st.font.name='Times New Roman'; st.font.size=Pt(sz); st.font.bold=True
        for key in ('ascii','hAnsi','eastAsia'): st._element.rPr.rFonts.set(qn('w:'+key),'Times New Roman')

    # Cover
    add_center(d,'TRƯỜNG ĐẠI HỌC VĂN LANG',14,5)
    add_center(d,'KHOA LUẬT',14,54)
    add_center(d,'BÀI TẬP NHÓM SỐ 1',17,9)
    add_center(d,'MÔN HỌC: PHÁP LUẬT KINH DOANH BẤT ĐỘNG SẢN',14,34)
    add_center(d,'ĐỀ TÀI:',14,5)
    add_center(d,'KINH DOANH DỊCH VỤ SÀN GIAO DỊCH BẤT ĐỘNG SẢN:',15,3)
    add_center(d,'NHỮNG VẤN ĐỀ LÝ LUẬN VÀ THỰC TIỄN',15,48)
    for label,value in [('Nhóm thực hiện:','Nhóm 5'),('Mã lớp học phần:','261_71LAWS40482_01'),('Giảng viên hướng dẫn:','ThS. Trần Minh Toàn')]:
        p=d.add_paragraph(); p.paragraph_format.left_indent=Cm(3.4); p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(5); p.paragraph_format.line_spacing=1.1
        p.paragraph_format.tab_stops.add_tab_stop(Cm(7.2),WD_TAB_ALIGNMENT.LEFT,WD_TAB_LEADER.SPACES); set_font(p.add_run(label+'\t'+value),13)
    p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(48); p.paragraph_format.first_line_indent=Cm(0)
    set_font(p.add_run('Thành phố Hồ Chí Minh, ngày 12 tháng 10 năm 2026'),13,italic=True)

    # Members / acknowledgment / declaration
    s2=d.add_section(WD_SECTION_START.NEW_PAGE); set_margins(s2); s2.footer.is_linked_to_previous=False; set_numbering(s2,'lowerRoman',1)
    f=s2.footer.paragraphs[0]; clear_p(f); f.alignment=WD_ALIGN_PARAGRAPH.CENTER; add_field(f,'PAGE','i')
    add_heading(d,'DANH SÁCH THÀNH VIÊN NHÓM VÀ BẢNG PHÂN CÔNG',1)
    tbl=d.add_table(rows=0,cols=5); tbl.alignment=WD_TABLE_ALIGNMENT.CENTER; tbl.autofit=False
    widths=[Cm(.85),Cm(3.5),Cm(2.7),Cm(6),Cm(1.55)]
    for ri,sr in enumerate(src.tables[0].rows):
        cells=tbl.add_row().cells
        for ci,c in enumerate(cells):
            c.width=widths[ci]; c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; cell_margins(c,55)
            p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER if ci in (0,2,4) or ri==0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
            set_font(p.add_run(' '.join(sr.cells[ci].text.split())),9.5 if ri else 10,ri==0)
    borders(tbl)
    h='Lời đầu tiên, nhóm nghiên cứu chúng em xin được gửi lời cảm ơn chân thành và sâu sắc nhất đến ThS. Trần Minh Toàn, giảng viên bộ môn Pháp luật Kinh doanh Bất động sản thuộc Khoa Luật, Trường Đại học Văn Lang. Trong suốt quá trình học tập và tiếp cận môn học, thầy đã truyền đạt kiến thức lý luận về chế độ pháp lý kinh doanh bất động sản, điều kiện thành lập và hoạt động của sàn giao dịch, đồng thời định hướng tư duy pháp lý thực tiễn qua các tình huống giao dịch và tranh chấp. Sự hướng dẫn của thầy đã giúp nhóm có cơ sở hoàn thành báo cáo. Do thời gian và năng lực nghiên cứu còn hạn chế, nhóm mong nhận được ý kiến đóng góp để tiếp tục hoàn thiện bài viết.'
    c='Nhóm nghiên cứu xin cam đoan báo cáo với đề tài “Kinh doanh dịch vụ sàn giao dịch bất động sản - những vấn đề lý luận và thực tiễn” là công trình nghiên cứu của các thành viên dưới sự hướng dẫn của giảng viên phụ trách. Các quy định pháp luật, tài liệu và tình huống được trình bày theo nguồn được liệt kê trong báo cáo; nhóm chịu trách nhiệm về tính trung thực của phần nội dung do nhóm thực hiện.'
    add_heading(d,'LỜI CẢM ƠN',2,True); add_body(d,h)
    p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.RIGHT; p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(3); set_font(p.add_run('Nhóm chúng em xin trân trọng cảm ơn!'),12)
    add_heading(d,'LỜI CAM ĐOAN',2,True); add_body(d,c)

    # Contents: a stable one-page list matching the page plan below.
    d.add_page_break(); add_heading(d,'MỤC LỤC',1)
    toc=[(0,'PHẦN MỞ ĐẦU','1'),(1,'1. Lý do chọn đề tài','1'),(1,'2. Mục tiêu và nhiệm vụ nghiên cứu','1'),(1,'3. Đối tượng, phạm vi và phương pháp','1'),
    (0,'CHƯƠNG I. CƠ SỞ LÝ LUẬN VÀ PHÁP LUẬT HIỆN HÀNH','2'),(1,'1.1. Khái niệm, bản chất và vai trò của sàn giao dịch','2'),(1,'1.2. Cơ sở pháp lý và định hướng điều chỉnh','2'),(1,'1.3. Điều kiện thành lập và hoạt động của sàn','3'),(1,'1.4. Điều kiện đối với hoạt động môi giới trong sàn','3'),(1,'1.5. Nội dung hoạt động, quyền và nghĩa vụ của sàn','4'),(1,'1.6. Hợp đồng dịch vụ và thanh toán','4'),
    (0,'CHƯƠNG II. THỰC TIỄN ÁP DỤNG VÀ NHỮNG VẤN ĐỀ PHÁT SINH','5'),(1,'2.1. Công khai và kiểm tra thông tin bất động sản','5'),(1,'2.2. Quảng cáo, thông tin về giá và nguy cơ gây hiểu nhầm','6'),(1,'2.3. Tranh chấp phí dịch vụ và trách nhiệm của các bên','6'),(1,'2.4. Sàn trực tuyến và chứng cứ giao dịch','7'),(1,'2.5. Giám sát và khó khăn khi áp dụng pháp luật','8'),
    (0,'CHƯƠNG III. KIẾN NGHỊ HOÀN THIỆN VÀ NÂNG CAO HIỆU QUẢ THI HÀNH','9'),(1,'3.1. Hoàn thiện thể chế và quy trình pháp lý','9'),(1,'3.2. Tổ chức thực hiện và bảo vệ khách hàng','9'),(0,'KẾT LUẬN VÀ DANH MỤC TÀI LIỆU THAM KHẢO','10')]
    tt=d.add_table(rows=0,cols=2); tt.alignment=WD_TABLE_ALIGNMENT.CENTER; tt.autofit=False
    for lev,label,num in toc:
        cells=tt.add_row().cells; cells[0].width=Cm(13.8); cells[1].width=Cm(1.1)
        for ix,cell in enumerate(cells):
            cell_margins(cell,20); p=cell.paragraphs[0]; p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
            p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ix==0 else WD_ALIGN_PARAGRAPH.RIGHT
            if ix==0 and lev: p.paragraph_format.left_indent=Cm(.35)
            set_font(p.add_run(label if ix==0 else num),11.5,lev==0)
    borders(tt,True)

    # Body section resets numbering and prints exactly ten substantive pages.
    s3=d.add_section(WD_SECTION_START.NEW_PAGE); set_margins(s3); s3.footer.is_linked_to_previous=False; set_numbering(s3,'decimal',1)
    f=s3.footer.paragraphs[0]; clear_p(f); f.alignment=WD_ALIGN_PARAGRAPH.CENTER
    set_font(f.add_run('Trang '),11); add_field(f,'PAGE','1'); set_font(f.add_run(' / 10'),11)
    for i,(title,sections) in enumerate(PAGES):
        if i: d.add_page_break()
        add_heading(d,title,1)
        for sub,pars in sections:
            add_heading(d,sub,2)
            for text in pars: add_body(d,text)
    d.add_page_break(); add_heading(d,'KẾT LUẬN VÀ DANH MỤC TÀI LIỆU THAM KHẢO',1)
    add_heading(d,'KẾT LUẬN',2,True)
    for text in CONCLUSION: add_body(d,text)
    add_heading(d,'DANH MỤC TÀI LIỆU THAM KHẢO',2,True)
    for i,text in enumerate(REFERENCES,1):
        p=d.add_paragraph(); p.paragraph_format.left_indent=Cm(.65); p.paragraph_format.first_line_indent=Cm(-.65); p.paragraph_format.space_after=Pt(2); p.paragraph_format.line_spacing=1.05
        set_font(p.add_run(f'[{i}] {text}'),11.5)
    for sec in d.sections: set_margins(sec)
    d.core_properties.title='Kinh doanh dịch vụ sàn giao dịch bất động sản - Nhóm 5'; d.core_properties.subject='Bài tập nhóm Khoa Luật'; d.core_properties.author='Nhóm 5'
    d.save(OUT); print('SAVED',OUT,'PAGES_OF_CONTENT',len(PAGES)+1)

if __name__=='__main__': create()
